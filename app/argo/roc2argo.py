from typing import cast

from pydantic import BaseModel
from rocrate.rocrate import ROCrate

from app.argo.models import Annotations, Author, Workflow, WorkflowMetadata
from app.workflow_engines.base import WorkflowEngine


def generate_workflow_from_rocrate(
    crate: ROCrate, workflow: dict, engine: WorkflowEngine
) -> Workflow:

    annotations = (
        workflow["metadata"]["annotations"]
        if "metadata" in workflow and "annotations" in workflow["metadata"]
        else {}
    )

    annotations = _update_annotations(crate)
    metadata = WorkflowMetadata(annotations=annotations, labels={})

    return Workflow(
        kind="Workflow",
        metadata=metadata,
        spec=workflow["spec"],
    )


def _update_annotations(crate: ROCrate) -> Annotations:

    class ROCrateMetadata(BaseModel):
        name: str
        description: str
        license: str
        keywords: list[str]

    metadata = ROCrateMetadata.model_validate(
        {
            "name": crate.root_dataset["name"],
            "description": crate.root_dataset["description"],
            "license": crate.root_dataset["license"],
            "keywords": crate.root_dataset["keywords"],
        }
    )

    return Annotations(
        title=metadata.name,
        description=metadata.description,
        license=metadata.license,
        keywords=metadata.keywords,
        authors=_get_authors(crate),
    )


def _get_authors(crate: ROCrate) -> list[Author]:
    if isinstance(crate.root_dataset["author"], str):
        author = crate.get(crate.root_dataset["author"])
        if author is None:
            raise ValueError("Author not found in the RO-Crate.")
        return [Author(name=author["name"], id=author["@id"])]

    elif isinstance(crate.root_dataset["author"], list):
        authors = []
        for author in crate.root_dataset["author"]:
            author = cast(dict, author)
            authors.append(Author(name=author["name"], id=author["@id"]))
        return authors

    raise ValueError("Author not found in the RO-Crate.")
