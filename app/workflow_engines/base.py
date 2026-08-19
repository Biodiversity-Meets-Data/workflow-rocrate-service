from abc import ABC, abstractmethod

from app.models import Workflow


class WorkflowEngine(ABC):
    name: str
    annotations_prefix: str
    labels_prefix: str = "workflows.argoproj.io"
    base_url: str

    @abstractmethod
    def get_workflow(self, workflow_id: str, token: str) -> Workflow:
        pass

    @abstractmethod
    def post_workflow(self, workflow_data: dict, token: str) -> Workflow:
        pass
