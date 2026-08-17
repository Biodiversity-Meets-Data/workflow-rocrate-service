import requests

from app.workflow_engines.base import WorkflowEngine


class LifeWatchEngine(WorkflowEngine):
    name: str = "lifewatch"
    annotations_prefix: str = "lifewatch"
    base_url: str = "https://workflows-demo.bmd.lifewatch.dev/v1"

    def get_workflow(self, workflow_id: str, token: str) -> dict:

        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(
            f"{self.base_url}/{workflow_id}/status", headers=headers
        )
        response.raise_for_status()

        return response.json()

    def post_workflow(self, workflow_data: dict, token: str):
        pass
