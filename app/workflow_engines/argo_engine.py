from hera.exceptions import NotFound as HeraNotFoundException
from hera.exceptions import Unauthorized
from hera.workflows import WorkflowsService
from pydantic import ValidationError
from requests.exceptions import ConnectionError

from app.argo.models import Workflow
from app.exceptions import (
    UpstreamWorkflowEngineError,
    WorkflowNotFoundError,
    WorkflowParsingError,
)
from app.workflow_engines.base import WorkflowEngine


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
        argo_token: str,
        argo_host: str,
        argo_namespace: str,
    ):
        self.name = "argo"
        self.annotations_prefix = annotations_prefix
        self.labels_prefix = labels_prefix
        self.base_url = base_url
        self.argo_token = argo_token
        self.argo_host = argo_host
        self.argo_namespace = argo_namespace
        self.workflows_service = WorkflowsService(
            host=argo_host,
            namespace=argo_namespace,
            token=argo_token,
        )

    def authenticate(self, token: str) -> None:
        return  # No authentication needed for the argo engine

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
        return "dummy_workflow_id"
