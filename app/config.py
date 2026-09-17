from app.settings import (
    app_settings,
    dummy_engine_settings,
    lifewatch_engine_settings,
)
from app.workflow_engines.base import WorkflowEngine
from app.workflow_engines.dummy_engine import DummyEngine
from app.workflow_engines.lifewatch_engine import LifeWatchEngine


class Settings:
    def __init__(self):
        self.app_name = app_settings.app_name
        self.engines: dict[str, WorkflowEngine] = {
            "lifewatch": LifeWatchEngine(
                keycloak_issuer=lifewatch_engine_settings.keycloak_issuer,
                base_url=lifewatch_engine_settings.base_url,
                annotations_prefix=lifewatch_engine_settings.annotations_prefix,
                labels_prefix=lifewatch_engine_settings.labels_prefix,
            ),
            "dummy": DummyEngine(
                annotations_prefix=dummy_engine_settings.annotations_prefix,
                labels_prefix=dummy_engine_settings.labels_prefix,
                base_url=dummy_engine_settings.base_url,
            ),
        }


settings = Settings()
