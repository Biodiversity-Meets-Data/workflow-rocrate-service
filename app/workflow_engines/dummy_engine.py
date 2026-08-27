import json

from app.argo.models import Workflow
from app.workflow_engines.base import WorkflowEngine


class DummyEngine(WorkflowEngine):
    name: str = "dummy"
    annotations_prefix: str = "dummy"
    base_url: str = f"http://localhost:8000/workflow-engines/{name}/workflows"

    def authenticate(self, token: str) -> None:
        return  # No authentication needed for the dummy engine

    def get_workflow(self, workflow_id: str, token: str) -> Workflow:
        with open("tests/fixtures/successful_workflow.json") as f:
            workflow = json.load(f)
        return self.parse_workflow(workflow)

    def post_workflow(self, workflow_data: dict, token: str):
        pass
