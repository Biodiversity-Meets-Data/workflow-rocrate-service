from typing import Any

from app.models import Workflow


def reconstruct_workflow(wfl: Workflow, annotations_prefix: str) -> dict[str, Any]:
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
        "spec": wfl.spec,
    }

    return reconstructed


def reconstruct_template(wfl: Workflow) -> dict[str, Any]:
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
