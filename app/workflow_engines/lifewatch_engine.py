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

        status = response.json()
        template_spec = status.get("storedWorkflowTemplateSpec", {})
        annotations = template_spec.get("workflowMetadata", {}).get("annotations", {})
        if not annotations:
            annotations = {}

        data = {}
        data["metadata"] = {
            "name": workflow_id,
            "annotations": {
                f"{self.annotations_prefix}/author_names": annotations.get(
                    f"{self.annotations_prefix}/author_names", "unknown"
                ),
                f"{self.annotations_prefix}/author_ids": annotations.get(
                    f"{self.annotations_prefix}/author_ids", "unknown"
                ),
                f"{self.annotations_prefix}/license": annotations.get(
                    f"{self.annotations_prefix}/license", "unknown"
                ),
                f"{self.annotations_prefix}/keywords": annotations.get(
                    f"{self.annotations_prefix}/keywords", "unknown"
                ),
                "workflows.argoproj.io/description": annotations.get(
                    "workflows.argoproj.io/description", "unknown"
                ),
                "workflows.argoproj.io/title": annotations.get(
                    "workflows.argoproj.io/title", "unknown"
                ),
            },
            "labels": {
                f"{self.labels_prefix}/creator": template_spec.get(
                    "workflowMetadata", {}
                )
                .get("labels", {})
                .get(f"{self.labels_prefix}/creator", "unknown")
            },
        }

        data["spec"] = {
            "workflowTemplateRef": template_spec.get("workflowTemplateRef", {}),
            "arguments": template_spec.get("arguments", {}),
        }
        data["status"] = status
        try:
            wfl = self.parse_workflow(data)
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
            "workflow_template_ref": {"name": workflow_template_ref["name"]},
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self.api_endpoint + "/submit/from_template",
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
