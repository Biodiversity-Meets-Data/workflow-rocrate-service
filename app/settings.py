from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "workflow-rocrate-service"


class LifeWatchEngineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LIFEWATCH_", env_file=".env", extra="ignore"
    )

    keycloak_issuer: str = "link-to-lifewatch-keycloak-issuer"
    base_url: str = "link-to-lifewatch-workflow-base-url"
    annotations_prefix: str = "lifewatch"
    labels_prefix: str = "workflows.lifewatch.eu"


class DummyEngineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DUMMY_", env_file=".env", extra="ignore"
    )

    annotations_prefix: str = "dummy"
    labels_prefix: str = "workflows.argoproj.io"
    base_url: str = "http://localhost:8000/workflow-engines/dummy/workflows"


class LocalEngineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOCAL_", env_file=".env", extra="ignore"
    )

    annotations_prefix: str = "tbd"
    labels_prefix: str = "tbd"
    base_url: str = "http://localhost:8000/workflow-engines/local/workflows"
    argo_token: str = "local-argo-token"
    argo_host: str = "http://localhost:2746"
    argo_namespace: str = "argo"


app_settings = AppSettings()
lifewatch_engine_settings = LifeWatchEngineSettings()
dummy_engine_settings = DummyEngineSettings()
local_engine_settings = LocalEngineSettings()
