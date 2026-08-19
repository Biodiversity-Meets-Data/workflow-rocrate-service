import json

from app.models import Workflow
from app.workflow_engines.base import WorkflowEngine


class DummyEngine(WorkflowEngine):
    name: str = "dummy"
    annotations_prefix: str = "dummy"
    base_url: str = f"http://localhost:8000/workflow-engines/{name}/workflows"

    def get_workflow(self, workflow_id: str, token: str) -> Workflow:
        with open("tests/fixtures/successful_workflow.json") as f:
            workflow = json.load(f)
        return Workflow(**workflow)

    def post_workflow(self, workflow_data: dict, token: str):
        pass
