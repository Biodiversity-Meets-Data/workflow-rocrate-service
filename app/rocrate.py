from datetime import UTC, datetime
from typing import Any, cast

from rocrate.model import ContextEntity, File, Person
from rocrate.rocrate import ROCrate
from rocrate_validator.services import validate_metadata_as_dict


def generate_WROC_from_workflow(
    wfl: dict[str, Any], prefix: str, base_url: str
) -> ROCrate:
    crate = ROCrate()

    _add_workflow_annotations(wfl, crate, prefix)
    wfl_object = _add_workflow_files(wfl, crate, base_url)
    _add_workflow_params(wfl, crate, wfl_object)

    crate.metadata.profile = "https://w3id.org/ro/crate/1.1"
    crate.metadata["conformsTo"] = [
        {"@id": "https://w3id.org/ro/crate/1.1"},
        {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
    ]

    _add_date_published(wfl, crate)

    validate_rocrate(crate)
    return crate


def _add_date_published(wfl: dict[str, Any], crate: ROCrate):
    if wfl["metadata"].get("creationTimestamp"):
        dt = datetime.fromisoformat(wfl["metadata"]["creationTimestamp"])

    else:
        dt = datetime.now(UTC)
    crate.root_dataset["datePublished"] = dt.isoformat()


def _add_workflow_annotations(wfl: dict[str, Any], crate: ROCrate, prefix: str):

    workflow_annotations = wfl["metadata"]["annotations"]

    required_fields = [
        f"{prefix}/author_names",
        f"{prefix}/author_ids",
        f"{prefix}/license",
        f"{prefix}/keywords",
        "workflows.argoproj.io/description",
        "workflows.argoproj.io/title",
    ]

    for field in required_fields:
        if field not in workflow_annotations:
            raise ValueError(f"Missing required annotation: {field}")

    author_names = [
        author_name.strip()
        for author_name in workflow_annotations[f"{prefix}/author_names"].split(",")
    ]

    author_ids = [
        f"https://orcid.org/{author_id.strip()}"
        for author_id in workflow_annotations[f"{prefix}/author_ids"].split(",")
    ]

    if len(author_names) != len(author_ids):
        raise ValueError("The number of author names and author IDs must be the same.")

    for name, identifier in zip(author_names, author_ids):
        author = cast(
            Person,
            crate.add(Person(crate, identifier=identifier, properties={"name": name})),
        )

        crate.root_dataset["author"] = {"@id": author["@id"]}

    crate.root_dataset["license"] = workflow_annotations[f"{prefix}/license"]

    crate.root_dataset["keywords"] = [
        keyword.strip()
        for keyword in workflow_annotations[f"{prefix}/keywords"].split(",")
    ]

    crate.root_dataset["description"] = workflow_annotations[
        "workflows.argoproj.io/description"
    ]

    crate.root_dataset["name"] = workflow_annotations["workflows.argoproj.io/title"]


def _add_workflow_files(wfl: dict[str, Any], crate: ROCrate, base_url: str) -> File:
    workflow_id = wfl["metadata"]["name"]

    # Add the Argo workflow language context entity to the RO-Crate
    crate.add(
        ContextEntity(
            crate,
            identifier="https://argoproj.github.io/workflows",
            properties={
                "@type": "ComputerLanguage",
                "name": "Argo",
                "description": "Argo workflow language",
                "url": "https://argoproj.github.io/workflows",
            },
        )
    )

    # Add the workflow.yaml file to the RO-Crate
    workflow_object = crate.add_file(
        source=f"{base_url}/{workflow_id}/workflow.yaml",
        properties={
            "@type": ["File", "ComputationalWorkflow", "SoftwareSourceCode"],
            "programmingLanguage": {"@id": "https://argoproj.github.io/workflows"},
            "description": "Argo workflow definition",
            "encodingFormat": "text/yaml",
            "author": [
                {"@id": author["@id"]} for author in crate.get_by_type("Person")
            ],
            "name": "workflow.yaml",
            "softwareRequirements": {"@id": f"{base_url}/{workflow_id}/template.yaml"},
        },
    )

    workflow_object = cast(File, workflow_object)

    crate.root_dataset["mainEntity"] = {"@id": workflow_object["@id"]}

    # Add the template.yaml file to the RO-Crate if it exists
    if "workflowTemplateRef" in wfl["spec"]:
        wfl["spec"]["workflowTemplateRef"]["name"]
        crate.add_file(
            source=f"{base_url}/{workflow_id}/template.yaml",
            properties={
                "@type": ["File", "ComputationalWorkflow", "SoftwareSourceCode"],
                "programmingLanguage": {"@id": "https://argoproj.github.io/workflows"},
                "description": "Argo workflow template definition",
                "encodingFormat": "text/yaml",
                "author": [
                    {"@id": author["@id"]} for author in crate.get_by_type("Person")
                ],
                "name": "template.yaml",
            },
        )

    return workflow_object


def _add_workflow_params(wfl: dict[str, Any], crate: ROCrate, workflow_object: File):

    if not "arguments" in wfl["spec"]:
        return

    if not "parameters" in wfl["spec"]["arguments"]:
        return

    for param in wfl["spec"]["arguments"]["parameters"]:
        formal_param = crate.add_formal_parameter(
            identifier=f"#{param['name']}",
            name=param["name"],
            description=param.get("description", ""),
            additionalType="Text",
            defaultValue=param.get("default", ""),
        )

        workflow_object.append_to("input", formal_param)


def validate_rocrate(crate: ROCrate):
    settings = {"profile_identifier": "workflow-ro-crate-1.0"}
    metadata_dict = crate.metadata.generate()
    validation_result = validate_metadata_as_dict(metadata_dict, settings=settings)

    if not validation_result.has_issues():
        print("RO-Crate is valid")
    else:
        error_message = f"RO-Crate is invalid. There are {len(validation_result.get_issues())} issues:\n"
        for issue in validation_result.get_issues():
            error_message += f'Detected issue of severity {issue.severity.name} with check "{issue.check.identifier}": {issue.message}\n'
        raise ValueError(error_message)
    return validation_result
