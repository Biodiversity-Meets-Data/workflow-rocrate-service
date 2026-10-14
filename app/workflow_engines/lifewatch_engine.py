import json
from collections.abc import Iterator
from pathlib import PurePosixPath

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

    def submit_workflow(
        self, workflow: Workflow, token: str, callback_url: str | None = None
    ) -> str:

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
            "accept": "application/json",
        }

        response = requests.post(
            self.api_endpoint + "/submit/from_template",
            headers=headers,
            data=json.dumps(payload),
        )
        if (response.status_code == 404) & ("Template not found" in response.text):
            raise WorkflowParsingError(
                "Failed to submit workflow to LifeWatch, referenced template not found"
            )

        response.raise_for_status()
        workflow_id = response.json().get("name")
        return workflow_id

    def iterate_attached_artifacts(
        self,
        workflow_status: WorkflowStatus,
        workflow_id: str,
        token: str | None = None,
    ) -> Iterator[EngineArtifactStream]:
        if token is None:
            raise AuthenticationError("LifeWatch access token is required")

        if workflow_status.storedWorkflowTemplateSpec is None:
            raise WorkflowParsingError(
                f"Failed to iterate attached artifacts for workflow {workflow_id}, stored workflow template spec is missing"
            )

        bucket_name = workflow_status.storedWorkflowTemplateSpec["workflowMetadata"][
            "labels"
        ]["workflows.lifewatch.eu/creator"]

        for node in workflow_status.nodes.values():
            if node.outputs is None:
                continue

            for artifact in node.outputs.artifacts:
                if artifact.artifactGC is not None:
                    strategy = artifact.artifactGC.get("strategy")
                    if strategy == "OnWorkflowCompletion":
                        continue

                object_prefix = artifact.s3.key + "/"
                presigned_urls = self._get_presigned_artifact_urls(
                    object_prefix, bucket_name, token
                )

                for file in presigned_urls:
                    object_name = file["objectName"]
                    download_url = file["preSignedUrl"]
                    crate_path = (
                        node.id
                        + "/"
                        + artifact.name
                        + "/"
                        + object_name.removeprefix(object_prefix)
                    )

                    response = requests.get(download_url, stream=True)
                    response.raise_for_status()

                    content_type = response.headers.get("Content-Type")
                    encoding_format = (
                        content_type.split(";", 1)[0].strip() if content_type else None
                    )
                    content_size = _parse_content_size(
                        response.headers.get("Content-Length")
                    )

                    yield EngineArtifactStream(
                        crate_path=crate_path,
                        name=PurePosixPath(crate_path).name,
                        content_stream=_iter_content_and_close(response),
                        encoding_format=encoding_format,
                        content_size=content_size,
                    )

    def _get_presigned_artifact_urls(
        self,
        object_prefix: str,
        bucket_name: str,
        token: str,
    ) -> list[dict[str, str]]:

        base_url = "https://api-tesseract.beta.my.lifewatch.dev/api/files/preSignedGetObjectUrl"
        headers = {
            "Accept": "application/json",
            "Origin": "https://beta.my.lifewatch.dev",
            "Authorization": f"Bearer {token}",
        }
        response = requests.get(
            base_url,
            params={"bucketName": bucket_name, "objectName": object_prefix},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()["preSignedUrls"]


def _iter_content_and_close(response: requests.Response) -> Iterator[bytes]:
    try:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                yield chunk
    finally:
        response.close()


def _parse_content_size(content_size_header: str | None) -> int | None:
    if content_size_header is None:
        return None

    try:
        return int(content_size_header)
    except ValueError:
        return None
