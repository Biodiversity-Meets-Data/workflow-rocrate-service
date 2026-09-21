from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class ArgoBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_snake,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class ArtifactS3(ArgoBaseModel):
    key: str


class Artifact(ArgoBaseModel):
    name: str
    path: str | None = None
    s3: ArtifactS3


class NodeOutputs(ArgoBaseModel):
    artifacts: list[Artifact]


class Node(ArgoBaseModel):
    name: str
    outputs: NodeOutputs | None = None


class ArtifactRepositoryS3(ArgoBaseModel):
    bucket: str
    endpoint: str


class ArtifactRepository(ArgoBaseModel):
    s3: ArtifactRepositoryS3


class ArtifactRepositoryRef(ArgoBaseModel):
    artifactRepository: ArtifactRepository


class WorkflowStatus(ArgoBaseModel):
    nodes: dict[str, Node]
    phase: Literal["Pending", "Running", "Succeeded", "Failed", "Error"]
    artifactRepositoryRef: ArtifactRepositoryRef
    startedAt: datetime
    finishedAt: datetime | None = None
    storedWorkflowTemplateSpec: dict | None = None


class Parameter(ArgoBaseModel):
    name: str
    value: str
    description: str | None = None
    default: str | None = None


class Arguments(ArgoBaseModel):
    parameters: list[Parameter] | None = None


class WorkflowSpec(ArgoBaseModel):
    arguments: Arguments | None = None
    workflowTemplateRef: dict | None = None
    entrypoint: str | None = None
    templates: list[dict] | None = None


class Author(ArgoBaseModel):
    name: str
    id: str


class Annotations(ArgoBaseModel):
    authors: list[Author]
    license: str
    keywords: list[str]
    description: str
    title: str


class WorkflowMetadata(ArgoBaseModel):
    name: str | None = None
    generateName: str | None = None
    annotations: Annotations
    labels: dict
    creationTimestamp: datetime | None = None


class Workflow(ArgoBaseModel):
    kind: Literal["Workflow", "WorkflowTemplate"] = "Workflow"
    metadata: WorkflowMetadata
    spec: WorkflowSpec
    status: WorkflowStatus | None = None


class WorkflowRun(Workflow):
    status: WorkflowStatus  # pyright: ignore[reportGeneralTypeIssues]
