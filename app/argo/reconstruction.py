from typing import Any

from app.argo.models import Workflow
from app.workflow_engines.base import WorkflowEngine


def reconstruct_workflow(wfl: Workflow, engine: WorkflowEngine) -> dict[str, Any]:
    """
    Reconstructs a Workflow object into a dictionary representation, preserving specific `metadata` fields,
    retaining the full `spec` of the workflow, and omitting the `status` information.
    """

    wfl_dict = engine.serialize_workflow(wfl)

    wfl_dict.pop("status", None)
    wfl_dict["metadata"].pop("name", None)
    wfl_dict["metadata"].pop("creationTimestamp", None)
    wfl_dict["metadata"].pop("labels", None)

    return wfl_dict


def reconstruct_template(wfl: Workflow) -> dict[str, Any]:
    """
    Reconstructs a Workflow object into a dictionary representation of a WorkflowTemplate,
    converting the `status.storedWorkflowTemplateSpec` into the `spec` of the WorkflowTemplate.
    """
    if (
        wfl.spec.workflowTemplateRef is not None
        and wfl.status is not None
        and wfl.status.storedWorkflowTemplateSpec is not None
    ):
        spec = {
            key: value
            for key, value in wfl.status.storedWorkflowTemplateSpec.items()
            if key in ["templates", "entrypoint", "arguments", "workflowMetadata"]
        }
        template = {
            "kind": "WorkflowTemplate",
            "metadata": {
                "name": wfl.spec.workflowTemplateRef["name"],
            },
            "spec": spec,
        }
        return template
    return {}


def reconstruct_workflow_run(wfl: Workflow, engine: WorkflowEngine) -> dict[str, Any]:
    """
    Returns the complete dictionary representation of the Workflow object, including all fields.
    Returns an empty dictionary if the `status` field is None,
    indicating that the workflow run has not been completed or is not available.
    """
    if wfl.status is None:
        return {}

    return engine.serialize_workflow(wfl)
