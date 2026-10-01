import json
from collections.abc import Iterator

import requests

from app.argo.models import Workflow, WorkflowStatus
from app.exceptions import (
    AuthenticationError,
    WorkflowNotFoundError,
    WorkflowParsingError,
)
from app.workflow_engines.base import EngineArtifactStream, WorkflowEngine


class LifeWatchEngine(WorkflowEngine):
    def __init__(
        self,
        *,
        base_url: str,
        annotations_prefix: str,
        labels_prefix: str,
        api_endpoint: str,
    ):
        self.name = "lifewatch"
        self.base_url = base_url
        self.annotations_prefix = annotations_prefix
        self.labels_prefix = labels_prefix
        self.api_endpoint = api_endpoint

    def health_check(self):
        pass

    def get_workflow(self, workflow_id: str, token: str | None = None) -> Workflow:
        if token is None:
            raise AuthenticationError("LifeWatch access token is required")
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}

        response = requests.get(
            f"{self.api_endpoint}/{workflow_id}/status", headers=headers
        )
        if response.status_code == 404:
            raise WorkflowNotFoundError(f"Workflow with ID {workflow_id} not found")
        response.raise_for_status()
        try:
            wfl = self.parse_workflow(response.json())
        except KeyError as e:
            raise WorkflowParsingError(
                f"Failed to parse workflow with ID {workflow_id}, missing key: {e.args[0]}"
            ) from e

        return wfl

    def submit_workflow(self, workflow: Workflow, token: str) -> str:

        if not workflow.spec.arguments or not workflow.spec.arguments.parameters:
            parameters = []
        else:
            parameters = [
                param.model_dump() for param in workflow.spec.arguments.parameters
            ]

        workflow_template_ref = workflow.spec.workflowTemplateRef
        if not workflow_template_ref:
            raise WorkflowParsingError(
                "Failed to submit workflow to LifeWatch, workflow template reference is required"
            )

        payload = {
            "parameters": parameters,
            "workflow_template_ref": {"name": "bmd-terrestrial-sdm"},
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self.base_url + "/submit/from_template",
            headers=headers,
            data=json.dumps(payload),
        )
        response.raise_for_status()
        workflow_id = response.json().get("name")
        return workflow_id

    def iterate_attached_artifacts(
        self,
        workflow_status: WorkflowStatus,
        workflow_id: str,
    ) -> Iterator[EngineArtifactStream]:
        raise NotImplementedError(
            "Attached artifact streaming is not implemented for LifeWatch engine"
        )

    def get_artifact_download_url(self, workflow_id: str, artifact_key: str) -> str:
        raise NotImplementedError("Not implemented yet for LifeWatch engine")
