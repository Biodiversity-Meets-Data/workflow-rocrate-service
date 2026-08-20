from typing import Any

from app.argo.models import Workflow


def reconstruct_workflow(wfl: Workflow, annotations_prefix: str) -> dict[str, Any]:
    """
    Reconstructs a Workflow object into a dictionary representation, preserving specific `metadata` fields,
    retaining the full `spec` of the workflow, and omitting the `status` information.
    """
    annotation_keys_to_keep = [
        f"{annotations_prefix}/author_names",
        f"{annotations_prefix}/author_ids",
        f"{annotations_prefix}/keywords",
        f"{annotations_prefix}/license",
        "workflows.argoproj.io/description",
        "workflows.argoproj.io/title",
    ]
    annotations = {
        key: wfl.metadata["annotations"][key]
        for key in annotation_keys_to_keep
        if key in wfl.metadata.get("annotations", {})
    }

    metadata = {}

    if "generateName" in wfl.metadata:
        metadata["generateName"] = wfl.metadata["generateName"]
    if annotations not in (None, {}):
        metadata["annotations"] = annotations

    reconstructed = {
        "kind": "Workflow",
        "metadata": metadata,
        "spec": wfl.spec.model_dump(),
    }

    return reconstructed


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


def reconstruct_workflow_run(wfl: Workflow) -> dict[str, Any]:
    """
    Returns the complete dictionary representation of the Workflow object, including all fields.
    Returns an empty dictionary if the `status` field is None,
    indicating that the workflow run has not been completed or is not available.
    """
    if wfl.status is None:
        return {}

    wfl_dict = wfl.model_dump()
    wfl_dict["metadata"]["managedFields"] = (
        None  # Remove managedFields to avoid unnecessary clutter
    )

    return wfl_dict
