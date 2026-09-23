import os
import urllib.parse
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import boto3
import requests
from bs4 import BeautifulSoup
from hera.exceptions import NotFound as HeraNotFoundException
from hera.exceptions import Unauthorized
from hera.workflows import Workflow as HeraWorkflow
from hera.workflows import WorkflowsService
from hera.workflows.models import WorkflowCreateRequest
from pydantic import ValidationError
from requests.exceptions import ConnectionError

from app.argo.models import Workflow, WorkflowStatus
from app.exceptions import (
    UpstreamWorkflowEngineError,
    WorkflowNotFoundError,
    WorkflowParsingError,
)
from app.workflow_engines.base import EngineArtifactStream, WorkflowEngine


@dataclass(frozen=True)
class ArgoConnectionConfig:
    token: str
    host: str
    namespace: str
    artifact_access_key: str
    artifact_secret_key: str
    artifact_endpoint: str


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
        argo: ArgoConnectionConfig,
    ):
        self.name = "argo"
        self.annotations_prefix = annotations_prefix
        self.labels_prefix = labels_prefix
        self.base_url = base_url
        self.argo_token = argo.token
        self.argo_host = argo.host
        self.argo_namespace = argo.namespace
        self.workflows_service = WorkflowsService(
            host=self.argo_host,
            namespace=self.argo_namespace,
            token=self.argo_token,
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=f"http://{argo.artifact_endpoint}",
            aws_access_key_id=argo.artifact_access_key,
            aws_secret_access_key=argo.artifact_secret_key,
        )

    def authenticate(self, token: str) -> None:
        return  # No authentication implemented for the argo engine

    def health_check(self) -> bool:
        try:
            self.workflows_service.list_workflows(limit="1")
            return True
        except Unauthorized:
            return False
        except ConnectionError:
            return False

    def get_workflow(self, workflow_id: str, token: str | None = None) -> Workflow:
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
        health = self.health_check()
        if not health:
            raise UpstreamWorkflowEngineError(
                f"{self.name} workflow engine is not healthy, cannot submit workflow"
            )

        wfl_dict = self.serialize_workflow(workflow, snake_case=True)

        hera_workflow = cast(HeraWorkflow, HeraWorkflow.from_dict(wfl_dict))
        try:
            created_wfl = self.workflows_service.create_workflow(
                WorkflowCreateRequest(workflow=hera_workflow.build()),  # type: ignore
                namespace=self.argo_namespace,
            )
        except HeraNotFoundException as e:
            raise WorkflowNotFoundError(f"Failed to create workflow, {e!s}")
        return created_wfl.metadata.name  # type: ignore

    def iterate_attached_artifacts(
        self,
        workflow_status: WorkflowStatus,
        workflow_id: str,
    ) -> Iterator[EngineArtifactStream]:
        bucket_name = workflow_status.artifactRepositoryRef.artifactRepository.s3.bucket
        artifact_url = self.base_url.rsplit("/", 1)[0]
        argo_token = self.argo_token

        for node in workflow_status.nodes.values():
            if node.outputs is None:
                continue

            for artifact in node.outputs.artifacts:
                if artifact.artifactGC is not None:
                    strategy = artifact.artifactGC.get("strategy")
                    if strategy == "OnWorkflowCompletion":
                        continue

                content_url = (
                    f"{artifact_url}/bucket/{bucket_name}/artifacts/{artifact.s3.key}"
                )

                argo_url = (
                    f"{self.argo_host}/artifact-files/argo/workflows/"
                    f"{workflow_id}/{node.id}/outputs/{artifact.name}"
                )

                file_path = artifact.path.lstrip("/") if artifact.path else ""
                initial_path = os.path.join(
                    node.id,
                    file_path,
                )

                for crate_path, content_stream in _recursive_artifact_reader(
                    url=argo_url,
                    argo_token=argo_token,
                    path=initial_path,
                ):
                    content_size_header = content_stream.headers.get("Content-Length")
                    content_size = _parse_content_size(content_size_header)
                    content_type = content_stream.headers.get("Content-Type")
                    encoding_format = (
                        content_type.split(";", 1)[0].strip() if content_type else None
                    )

                    yield EngineArtifactStream(
                        crate_path=crate_path,
                        name=os.path.basename(crate_path),
                        content_url=content_url,
                        content_stream=content_stream.content_stream,
                        encoding_format=encoding_format,
                        content_size=content_size,
                    )

    def get_artifact_download_url(self, bucket: str, artifact_key: str) -> str:

        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": artifact_key},
        )


def _recursive_artifact_reader(
    url: str,
    argo_token: str,
    path: str,
    verify_cert: bool = True,
    chunk_size: int = 1024 * 1024,
) -> Iterator[tuple[str, "ArtifactDownloadStream"]]:
    headers = {"Authorization": f"Bearer {argo_token}"}

    response = requests.get(
        url,
        verify=verify_cert,
        headers=headers,
        stream=True,
    )
    response.raise_for_status()

    is_download = "Content-Disposition" in response.headers

    if is_download:
        content_disposition = response.headers["Content-Disposition"]
        file_name = _get_filename_from_content_disposition(content_disposition)

        rewritten_path = os.path.join(
            os.path.dirname(path),
            file_name,
        )

        yield (
            rewritten_path,
            ArtifactDownloadStream(
                content_stream=_iter_content_and_close(response, chunk_size),
                headers=dict(response.headers),
            ),
        )
        return

    content = response.content
    response.close()

    soup = BeautifulSoup(content, features="html.parser")

    for link in soup.find_all("a"):
        href = link.get("href")

        if not isinstance(href, str) or href == "..":
            continue

        new_url = urllib.parse.urljoin(url + "/", href)
        new_path = os.path.join(path, href)

        yield from _recursive_artifact_reader(
            new_url,
            argo_token,
            new_path,
            verify_cert,
            chunk_size,
        )


def _get_filename_from_content_disposition(content_disposition: str) -> str:
    filename = content_disposition.split("filename=", 1)[-1].strip('"')
    return Path(filename).name


def _iter_content_and_close(
    response: requests.Response,
    chunk_size: int,
) -> Iterator[bytes]:
    try:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
    finally:
        response.close()


@dataclass(frozen=True)
class ArtifactDownloadStream:
    content_stream: Iterator[bytes]
    headers: dict[str, str]


def _parse_content_size(content_size_header: str | None) -> int | None:
    if content_size_header is None:
        return None

    try:
        return int(content_size_header)
    except ValueError:
        return None
