import os
from datetime import UTC, datetime
from typing import cast

from rocrate.model import ContextEntity, File, Person
from rocrate.rocrate import ROCrate
from rocrate_validator.services import validate_metadata_as_dict

from app.argo.models import Workflow, WorkflowRun, WorkflowStatus


def generate_WROC_from_workflow(
    wfl: Workflow, prefix: str, base_url: str, validate: bool = False
) -> ROCrate:
    crate = ROCrate()

    _add_metadata_from_annotations(wfl, crate, prefix)
    wfl_object = _add_workflow_definition_files(wfl, crate, base_url)
    _add_workflow_params(wfl, crate, wfl_object)

    crate.metadata.profile = "https://w3id.org/ro/crate/1.1"
    crate.metadata["conformsTo"] = [
        {"@id": "https://w3id.org/ro/crate/1.1"},
        {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
    ]

    _add_date_published(wfl, crate)
    if validate:
        validate_rocrate(crate, profile_identifier="workflow-ro-crate-1.0")
    return crate


def generate_WRROC_from_workflow(
    wfl: Workflow, prefix: str, base_url: str, validate: bool = False
) -> ROCrate:
    wfl = cast(WorkflowRun, wfl)
    crate = ROCrate()

    _add_metadata_from_annotations(wfl, crate, prefix)
    wfl_object = _add_workflow_definition_files(wfl, crate, base_url)
    _add_workflow_params(wfl, crate, wfl_object, wfl_run=True)
    _add_create_action(wfl, crate, wfl_object)
    _add_workflow_run_file(wfl, crate, base_url)
    _add_date_published(wfl, crate)
    wfl_status = wfl.status
    _add_artifacts(wfl_status, crate)
    crate.metadata.profile = "https://w3id.org/ro/crate/1.1"
    crate.metadata["conformsTo"] = [
        {"@id": "https://w3id.org/ro/crate/1.1"},
        {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
        {"@id": "https://w3id.org/ro/wfrun/process/0.5"},
        {"@id": "https://w3id.org/ro/wfrun/workflow/0.5"},
    ]

    _add_conforms_to(
        crate,
        profile_identifiers=[
            "ro/wfrun/process/0.5",
            "ro/wfrun/workflow/0.5",
            "workflowhub/workflow-ro-crate/1.0",
        ],
    )

    if validate:
        validate_rocrate(crate, profile_identifier="workflow-run-crate-0.5")
    return crate


def _add_workflow_run_file(wfl: WorkflowRun, crate: ROCrate, base_url: str):
    workflow_id = wfl.metadata.name
    create_action = cast(ContextEntity, crate.get_by_type("CreateAction")[0])

    # Add the workflow-run.yaml file to the RO-Crate
    workflow_run_object = cast(
        File,
        crate.add_file(
            source=f"{base_url}/{workflow_id}/workflow-run.yaml",
            properties={
                "@type": ["File"],
                "programmingLanguage": {"@id": "https://argoproj.github.io/workflows"},
                "description": "Argo workflow run",
                "encodingFormat": "text/yaml",
                "name": "workflow-run.yaml",
                "about": {"@id": create_action["@id"]},
            },
        ),
    )

    create_action["subjectOf"] = {"@id": workflow_run_object["@id"]}


def _add_conforms_to(crate: ROCrate, profile_identifiers: list[str]):
    conforms_to_entities = []
    for profile_identifier in profile_identifiers:
        conforms_to_entity = cast(
            ContextEntity,
            crate.add(
                ContextEntity(
                    crate,
                    identifier=f"https://w3id.org/{profile_identifier}",
                    properties={
                        "@type": "CreativeWork",
                        "version": profile_identifier.split("/")[-1],
                    },
                )
            ),
        )
        conforms_to_entities.append({"@id": conforms_to_entity["@id"]})

    crate.root_dataset["conformsTo"] = conforms_to_entities


def _add_date_published(wfl: Workflow, crate: ROCrate):
    if wfl.metadata.creationTimestamp:
        dt = wfl.metadata.creationTimestamp

    else:
        dt = datetime.now(UTC)
    crate.root_dataset["datePublished"] = dt.isoformat(timespec="seconds")


def _add_metadata_from_annotations(wfl: Workflow, crate: ROCrate, prefix: str):
    workflow_annotations = wfl.metadata.annotations

    for author in workflow_annotations.authors:
        author_object = cast(
            Person,
            crate.add(
                Person(crate, identifier=author.id, properties={"name": author.name})
            ),
        )
        crate.root_dataset.append_to("author", author_object)

    crate.root_dataset["license"] = workflow_annotations.license

    crate.root_dataset["keywords"] = workflow_annotations.keywords

    crate.root_dataset["description"] = workflow_annotations.description

    crate.root_dataset["name"] = workflow_annotations.title


def _add_create_action(wfl: WorkflowRun, crate: ROCrate, wfl_object: File):

    LABEL_PREFIX = "workflows.argoproj.io"

    agent = Person(
        crate,
        identifier="#workflow-agent",
        properties={
            "name": wfl.metadata.labels[f"{LABEL_PREFIX}/creator"],
        },
    )
    crate.add(agent)

    if wfl.status.phase == "Succeeded":
        actionStatus = "https://schema.org/CompletedActionStatus"
    elif wfl.status.phase == "Failed" or wfl.status.phase == "Error":
        actionStatus = "https://schema.org/FailedActionStatus"
    elif wfl.status.phase == "Running" or wfl.status.phase == "Pending":
        actionStatus = "https://schema.org/ActiveActionStatus"

    create_action = cast(
        ContextEntity,
        crate.add(
            ContextEntity(
                crate,
                identifier=f"#{wfl.metadata.name}-create-action",
                properties={
                    "@type": "CreateAction",
                    "object": [
                        {"@id": object["@id"]}
                        for object in crate.get_by_type("PropertyValue")
                    ],
                    "instrument": {"@id": wfl_object["@id"]},
                    "agent": {"@id": agent["@id"]},
                    "startTime": wfl.status.startedAt.isoformat(timespec="seconds"),
                    "endTime": wfl.status.finishedAt.isoformat(timespec="seconds")
                    if wfl.status.finishedAt
                    else None,
                    "actionStatus": {"@id": actionStatus},
                },
            )
        ),
    )

    crate.root_dataset["mentions"] = {"@id": create_action["@id"]}


def _add_workflow_definition_files(
    wfl: Workflow, crate: ROCrate, base_url: str
) -> File:
    workflow_id = wfl.metadata.name

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
    if wfl.spec.workflowTemplateRef is not None:
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


def _add_workflow_params(
    wfl: Workflow, crate: ROCrate, workflow_object: File, wfl_run: bool = False
):

    if wfl.spec.arguments is None:
        return

    if wfl.spec.arguments.parameters is None:
        return

    for param in wfl.spec.arguments.parameters:
        formal_param = cast(
            ContextEntity,
            crate.add_formal_parameter(
                identifier=f"#{param.name}",
                name=param.name,
                description=param.description,
                additionalType="Text",
                defaultValue=param.default,
            ),
        )

        workflow_object.append_to("input", formal_param)

        if wfl_run and param.value is not None:
            crate.add(
                ContextEntity(
                    crate,
                    identifier=f"#{param.name}-value",
                    properties={
                        "@type": "PropertyValue",
                        "name": param.name,
                        "description": param.description or "",
                        "additionalType": "Text",
                        "value": param.value,
                        "exampleOfWork": {"@id": formal_param["@id"]},
                    },
                )
            )


def _add_artifacts(wfl_status: WorkflowStatus, crate: ROCrate) -> None:
    s3_ref = wfl_status.artifactRepositoryRef.artifactRepository.s3

    create_action_object = crate.get_by_type("CreateAction")[0]
    for node_name, node in wfl_status.nodes.items():
        if node.outputs is None:
            continue

        for artifact in node.outputs.artifacts:
            if artifact.name == "main-logs":
                artifact_file = crate.add_file(
                    source=f"s3://{s3_ref.endpoint}:{s3_ref.bucket}:{artifact.s3.key}",
                    properties={
                        "name": "main.log",
                        "description": f"Main logs from node {node_name}",
                        "encodingFormat": "text/plain",
                    },
                )
            else:
                artifact_file = crate.add_file(
                    source=f"s3://{s3_ref.endpoint}:{s3_ref.bucket}:{artifact.s3.key}",
                    properties={
                        "name": os.path.basename(artifact.s3.key),
                        "description": f"Artifact {artifact.name} from node {node_name}",
                        "encodingFormat": "application/octet-stream",
                    },
                )

            create_action_object.append_to("result", artifact_file)


def validate_rocrate(
    crate: ROCrate, profile_identifier: str = "workflow-ro-crate-1.0"
) -> None:
    settings = {"profile_identifier": profile_identifier}
    metadata_dict = crate.metadata.generate()
    validation_result = validate_metadata_as_dict(metadata_dict, settings=settings)

    if validation_result.has_issues():
        error_message = f"RO-Crate is invalid. There are {len(validation_result.get_issues())} issues:\n"
        for issue in validation_result.get_issues():
            error_message += f'Detected issue of severity {issue.severity.name} with check "{issue.check.identifier}": {issue.message}\n'
        raise ValueError(error_message)
