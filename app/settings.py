from pathlib import Path
from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from app.auth import (
    AuthProvider,
    KeycloakJWTAuthProvider,
    StaticTokenAuthProvider,
)
from app.workflow_engines.argo_engine import ArgoConnectionConfig, ArgoWorkflowEngine
from app.workflow_engines.base import WorkflowEngine
from app.workflow_engines.dummy_engine import DummyEngine
from app.workflow_engines.lifewatch_engine import LifeWatchEngine


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    config_file: Path = Path(__file__).with_name("config.yaml")


class AppSettings(BaseModel):
    name: str


class StaticTokenAuthSettings(BaseModel):
    type: Literal["static_token"]
    token: SecretStr | None = None
    token_env: str | None = None


class KeycloakJWTAuthSettings(BaseModel):
    type: Literal["keycloak_jwt"]
    issuer: str
    audience: str | None = "account"
    algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    jwks_url: str | None = None


AuthSettings = Annotated[
    StaticTokenAuthSettings | KeycloakJWTAuthSettings,
    Field(discriminator="type"),
]


class DeploymentBase(BaseModel):
    base_url: str
    annotations_prefix: str
    labels_prefix: str
    auth: AuthSettings


class LifeWatchDeploymentSettings(DeploymentBase):
    engine: Literal["lifewatch"]
    api_endpoint: str


class DummyDeploymentSettings(DeploymentBase):
    engine: Literal["dummy"]


class ArgoSettings(BaseModel):
    token: SecretStr
    host: str
    namespace: str


class ArgoDeploymentSettings(DeploymentBase):
    engine: Literal["argo"]
    argo: ArgoSettings


DeploymentSettings = Annotated[
    LifeWatchDeploymentSettings | DummyDeploymentSettings | ArgoDeploymentSettings,
    Field(discriminator="engine"),
]


class ServiceSettings(BaseModel):
    app: AppSettings
    deployments: dict[str, DeploymentSettings]


class ServiceSettingsLoader(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppSettings
    deployments: dict[str, DeploymentSettings]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        runtime_settings = RuntimeSettings()
        yaml_source = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=runtime_settings.config_file,
        )

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_source,
            file_secret_settings,
        )


class AppRuntime(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_name: str
    engines: dict[str, WorkflowEngine]
    authenticators: dict[str, AuthProvider]


def _load_service_settings() -> ServiceSettings:
    runtime_settings = RuntimeSettings()
    config_file = runtime_settings.config_file

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    return ServiceSettings.model_validate(
        ServiceSettingsLoader.model_validate({}).model_dump()
    )


def _build_engine(settings: DeploymentSettings) -> WorkflowEngine:
    if isinstance(settings, LifeWatchDeploymentSettings):
        return LifeWatchEngine(
            base_url=settings.base_url,
            annotations_prefix=settings.annotations_prefix,
            labels_prefix=settings.labels_prefix,
            api_endpoint=settings.api_endpoint,
        )

    if isinstance(settings, DummyDeploymentSettings):
        return DummyEngine(
            annotations_prefix=settings.annotations_prefix,
            labels_prefix=settings.labels_prefix,
            base_url=settings.base_url,
        )

    return ArgoWorkflowEngine(
        annotations_prefix=settings.annotations_prefix,
        labels_prefix=settings.labels_prefix,
        base_url=settings.base_url,
        argo=ArgoConnectionConfig(
            token=settings.argo.token.get_secret_value(),
            host=settings.argo.host,
            namespace=settings.argo.namespace,
        ),
    )


def _build_auth_provider(settings: AuthSettings) -> AuthProvider:

    if isinstance(settings, StaticTokenAuthSettings):
        token_value = settings.token.get_secret_value() if settings.token else None
        token_env = settings.token_env

        if token_value and token_env:
            raise ValueError(
                "Static token auth must define either 'token' or 'token_env', not both"
            )

        return StaticTokenAuthProvider.from_value_or_env(
            token=token_value,
            token_env=token_env,
        )

    return KeycloakJWTAuthProvider(
        issuer=settings.issuer,
        audience=settings.audience,
        algorithms=settings.algorithms,
        jwks_url=settings.jwks_url,
    )


def _get_deployment(
    all_deployments: dict[str, DeploymentSettings],
    deployment_name: str,
    expected_type: type[DeploymentBase],
) -> DeploymentBase:
    deployment = all_deployments.get(deployment_name)
    if deployment is None:
        raise ValueError(
            f"Missing required deployment '{deployment_name}' in config.yaml"
        )
    if not isinstance(deployment, expected_type):
        raise TypeError(
            f"Deployment '{deployment_name}' must use engine '{expected_type.__name__}'"
        )
    return deployment


service_settings = _load_service_settings()


def get_deployment_as(
    deployment_name: str,
    expected_type: type[DeploymentBase],
) -> DeploymentBase:
    return _get_deployment(
        service_settings.deployments,
        deployment_name,
        expected_type,
    )


def get_argo_deployment(deployment_name: str) -> ArgoDeploymentSettings:
    return cast(
        ArgoDeploymentSettings,
        get_deployment_as(deployment_name, ArgoDeploymentSettings),
    )


def get_lifewatch_deployment(
    deployment_name: str = "lifewatch",
) -> LifeWatchDeploymentSettings:
    return cast(
        LifeWatchDeploymentSettings,
        get_deployment_as(deployment_name, LifeWatchDeploymentSettings),
    )


def get_dummy_deployment(deployment_name: str = "dummy") -> DummyDeploymentSettings:
    return cast(
        DummyDeploymentSettings,
        get_deployment_as(deployment_name, DummyDeploymentSettings),
    )


settings = AppRuntime(
    app_name=service_settings.app.name,
    engines={
        name: _build_engine(deployment)
        for name, deployment in service_settings.deployments.items()
    },
    authenticators={
        name: _build_auth_provider(deployment.auth)
        for name, deployment in service_settings.deployments.items()
    },
)
