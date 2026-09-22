from typing import cast

from pydantic import BaseModel
from rocrate.rocrate import ROCrate

from app.argo.models import Annotations, Author, Workflow, WorkflowMetadata


def generate_workflow_from_rocrate(
    crate: ROCrate,
    workflow: dict,
    workflow_parameters: dict,
) -> Workflow:

    metadata = workflow.get("metadata", {})
    annotations = metadata.get("annotations", {})

    annotations = _update_annotations(crate)

    metadata = WorkflowMetadata(
        annotations=annotations,
        labels={},
        generateName=metadata.get("generateName", None),
    )

    spec = workflow["spec"]

    params = _update_parameters(workflow_parameters, spec["arguments"]["parameters"])
    spec["arguments"]["parameters"] = params

    return Workflow(
        kind="Workflow",
        metadata=metadata,
        spec=spec,
    )


def _update_parameters(params_in: dict, params: list[dict]) -> list[dict]:
    """
    args:
        params_in: dict
            The new workflow parameters to be added.
        params: list
            The existing workflow parameters in the workflow spec.
    """

    for name, value in params_in.items():
        if name not in [param["name"] for param in params]:
            print(f"Parameter '{name}' not a recognized parameter.")
        else:
            for param in params:
                if param["name"] == name:
                    param["value"] = value
                    break

    return params


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

    if isinstance(crate.root_dataset["author"], list):
        authors = []
        for author in crate.root_dataset["author"]:
            author = cast(dict, author)
            authors.append(Author(name=author["name"], id=author["@id"]))
        return authors

    else:
        author = crate.root_dataset["author"]
        if author is None:
            raise ValueError("Author not found in the RO-Crate.")
        author = cast(dict, author)
        return [Author(name=author["name"], id=author["@id"])]
