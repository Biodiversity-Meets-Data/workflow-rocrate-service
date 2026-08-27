from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ArtifactS3(BaseModel):
    key: str


class Artifact(BaseModel):
    name: str
    path: str | None = None
    s3: ArtifactS3


class NodeOutputs(BaseModel):
    artifacts: list[Artifact]


class Node(BaseModel):
    name: str
    outputs: NodeOutputs | None = None


class ArtifactRepositoryS3(BaseModel):
    bucket: str
    endpoint: str


class ArtifactRepository(BaseModel):
    s3: ArtifactRepositoryS3


class ArtifactRepositoryRef(BaseModel):
    artifactRepository: ArtifactRepository


class WorkflowStatus(BaseModel):
    nodes: dict[str, Node]
    phase: Literal["Pending", "Running", "Succeeded", "Failed", "Error"]
    artifactRepositoryRef: ArtifactRepositoryRef
    startedAt: str
    finishedAt: str
    storedWorkflowTemplateSpec: dict | None = None


class Parameter(BaseModel):
    name: str
    value: str | None = None
    description: str | None = None
    default: str | None = None


class Arguments(BaseModel):
    parameters: list[Parameter] | None = None


class WorkflowSpec(BaseModel):
    arguments: Arguments | None = None
    workflowTemplateRef: dict | None = None


class WorkflowMetadata(BaseModel):
    name: str | None = None
    generateName: str | None = None
    annotations: dict[str, str]
    labels: dict
    creationTimestamp: datetime | None = None


class Workflow(BaseModel):
    metadata: WorkflowMetadata
    spec: WorkflowSpec
    status: WorkflowStatus | None = None


class WorkflowRun(Workflow):
    status: WorkflowStatus  # pyright: ignore[reportGeneralTypeIssues]
