from abc import ABC, abstractmethod


class WorkflowEngine(ABC):
    name: str
    annotations_prefix: str
    base_url: str

    @abstractmethod
    def get_workflow(self, workflow_id: str, token: str) -> dict:
        pass

    @abstractmethod
    def post_workflow(self, workflow_data: dict, token: str) -> dict:
        pass
