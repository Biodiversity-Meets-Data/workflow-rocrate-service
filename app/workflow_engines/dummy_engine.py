import json

from app.argo.models import Workflow
from app.workflow_engines.base import WorkflowEngine


class DummyEngine(WorkflowEngine):
    def __init__(self, *, annotations_prefix: str, labels_prefix: str, base_url: str):
        self.name = "dummy"
        self.annotations_prefix = annotations_prefix
        self.labels_prefix = labels_prefix
        self.base_url = base_url

    def authenticate(self, token: str) -> None:
        return  # No authentication needed for the dummy engine

    def health_check(self) -> bool:
        return True

    def get_workflow(self, workflow_id: str, token: str) -> Workflow:
        with open("tests/fixtures/successful_workflow.json") as f:
            workflow = json.load(f)
        return self.parse_workflow(workflow)

    def submit_workflow(self, workflow: Workflow, token: str) -> str:
        return "dummy_workflow_id"

    def get_artifact_download_url(self, workflow_id: str, artifact_key: str) -> str:
        return f"https://dummy.url/{workflow_id}/{artifact_key}"
