from pydantic_settings import BaseSettings

from app.workflow_engines.base import WorkflowEngine
from app.workflow_engines.dummy_engine import DummyEngine
from app.workflow_engines.lifewatch_engine import LifeWatchEngine


class Settings(BaseSettings):
    app_name: str = "workflow-rocrate-service"

    engines: dict[str, WorkflowEngine] = {
        "lifewatch": LifeWatchEngine(),
        "dummy": DummyEngine(),
    }


settings = Settings()
