from dataclasses import dataclass
from typing import cast

import boto3
from hera.exceptions import NotFound as HeraNotFoundException
from hera.exceptions import Unauthorized
from hera.workflows import Workflow as HeraWorkflow
from hera.workflows import WorkflowsService
from hera.workflows.models import WorkflowCreateRequest
from pydantic import ValidationError
from requests.exceptions import ConnectionError

from app.argo.models import Workflow
from app.exceptions import (
    UpstreamWorkflowEngineError,
    WorkflowNotFoundError,
    WorkflowParsingError,
)
from app.workflow_engines.base import WorkflowEngine


@dataclass(frozen=True)
class ArgoConnectionConfig:
    token: str
    host: str
    namespace: str
    artifact_access_key: str
    artifact_secret_key: str
    artifact_endpoint: str


class ArgoWorkflowEngine(WorkflowEngine):
    """
    This class allows to directly interact with an instance of Argo Workflows.
    """

    def __init__(
        self,
        *,
        annotations_prefix: str,
        labels_prefix: str,
        base_url: str,
        argo: ArgoConnectionConfig,
    ):
        self.name = "argo"
        self.annotations_prefix = annotations_prefix
        self.labels_prefix = labels_prefix
        self.base_url = base_url
        self.argo_token = argo.token
        self.argo_host = argo.host
        self.argo_namespace = argo.namespace
        self.workflows_service = WorkflowsService(
            host=self.argo_host,
            namespace=self.argo_namespace,
            token=self.argo_token,
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=f"http://{argo.artifact_endpoint}",
            aws_access_key_id=argo.artifact_access_key,
            aws_secret_access_key=argo.artifact_secret_key,
        )

    def authenticate(self, token: str) -> None:
        return  # No authentication implemented for the argo engine

    def health_check(self) -> bool:
        try:
            self.workflows_service.list_workflows(limit="1")
            return True
        except Unauthorized:
            return False
        except ConnectionError:
            return False

    def get_workflow(self, workflow_id: str, **kwargs) -> Workflow:
        health = self.health_check()
        if not health:
            raise UpstreamWorkflowEngineError(
                f"{self.name} workflow engine is not healthy, cannot retrieve workflow with ID {workflow_id}"
            )
        try:
            workflow = self.workflows_service.get_workflow(workflow_id)
        except HeraNotFoundException:
            raise WorkflowNotFoundError(f"Workflow with ID {workflow_id} not found")
        try:
            wfl_dict = workflow.dict()
            wfl_dict["kind"] = "Workflow"
            wfl = self.parse_workflow(wfl_dict)
        except KeyError as e:
            raise WorkflowParsingError(
                f"Failed to parse workflow with ID {workflow_id}, missing key: {e.args[0]}"
            ) from e
        except ValidationError as e:
            raise WorkflowParsingError(
                f"Failed to parse workflow with ID {workflow_id}, validation error: {e!s}"
            ) from e
        return wfl

    def submit_workflow(self, workflow: Workflow, token: str) -> str:
        health = self.health_check()
        if not health:
            raise UpstreamWorkflowEngineError(
                f"{self.name} workflow engine is not healthy, cannot submit workflow"
            )

        wfl_dict = self.serialize_workflow(workflow, snake_case=True)

        hera_workflow = cast(HeraWorkflow, HeraWorkflow.from_dict(wfl_dict))

        created_wfl = self.workflows_service.create_workflow(
            WorkflowCreateRequest(workflow=hera_workflow.build()),  # type: ignore
            namespace=self.argo_namespace,
        )
        return created_wfl.metadata.name  # type: ignore

    def get_artifact_download_url(self, bucket: str, artifact_key: str) -> str:

        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": artifact_key},
        )
