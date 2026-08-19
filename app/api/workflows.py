from typing import Annotated, Literal

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.argo.reconstruction import (
    reconstruct_template,
    reconstruct_workflow,
    reconstruct_workflow_run,
)
from app.argo.rocrate import generate_WROC_from_workflow, generate_WRROC_from_workflow
from app.config import settings
from app.exceptions import AuthenticationError
from app.workflow_engines.base import WorkflowEngine

router = APIRouter(prefix="/workflow-engines/{engine}/workflows", tags=["workflows"])

engines: dict[str, WorkflowEngine] = {
    "lifewatch": LifeWatchEngine(),
    "dummy": DummyEngine(),
}


def get_engine(name: str) -> WorkflowEngine:
    try:
        return engines[name]
    except KeyError:
        raise HTTPException(
            detail=f"Unknown workflow engine: {engine}",
            status_code=404,
        )
    return wfl_engine


bearer_scheme = HTTPBearer()


def check_auth(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    wfl_engine: WorkflowEngine = Depends(get_engine),
) -> str:
    try:
        wfl_engine.authenticate(token=credentials.credentials)
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )
    return credentials.credentials


@router.get("/{workflow_id}/workflow.yaml")
def get_workflow(
    engine: str,
    workflow_id: str,
    wfl_engine: WorkflowEngine = Depends(get_engine),
    token: str = Depends(check_auth),
):
    wfl = wfl_engine.get_workflow(workflow_id, token=token)
    wfl = reconstruct_workflow(wfl, wfl_engine.annotations_prefix)
    wfl = yaml.safe_dump(wfl, sort_keys=False)

    return Response(
        content=wfl,
        media_type="application/yaml",
        headers={"Content-Disposition": "attachment; filename=workflow.yaml"},
    )


@router.get("/{workflow_id}/template.yaml")
def get_template(
    engine: str,
    workflow_id: str,
    wfl_engine: WorkflowEngine = Depends(get_engine),
    token: str = Depends(check_auth),
):

    wfl = wfl_engine.get_workflow(workflow_id, token=token)
    template = reconstruct_template(wfl)
    print(template)

    if not template:
        return Response(
            content="No template found for this workflow.",
            media_type="text/plain",
            status_code=404,
        )

    template = yaml.safe_dump(template, sort_keys=False)

    return Response(
        content=template,
        media_type="application/yaml",
        headers={"Content-Disposition": "attachment; filename=template.yaml"},
    )


@router.get("/{workflow_id}/metadata")
def get_metadata(
    engine: str,
    workflow_id: str,
    profile: Annotated[
        Literal["WROC", "WRROC"],
        Query(
            description="Define which RO-Crate profile the returned metadata should conform to: "
            "Workflow RO-Crate ('WROC') or Workflow Run RO-Crate ('WRROC')."
        ),
    ] = "WROC",
    validate_rocrate: Annotated[
        bool,
        Query(
            description="This validates the generated RO-Crate against the RO-Crate profile schema. "
            "This is a slow operation and should be used mainly for testing purposes."
        ),
    ] = False,
    wfl_engine: WorkflowEngine = Depends(get_engine),
    token: str = Depends(check_auth),
):
    wfl = wfl_engine.get_workflow(workflow_id, token=token)

    try:
        if profile == "WROC":
            rocrate = generate_WROC_from_workflow(
                wfl,
                prefix=wfl_engine.annotations_prefix,
                base_url=wfl_engine.base_url,
                validate=validate_rocrate,
            )
        elif profile == "WRROC":
            rocrate = generate_WRROC_from_workflow(
                wfl,
                prefix=wfl_engine.annotations_prefix,
                base_url=wfl_engine.base_url,
                validate=validate_rocrate,
            )
    except ValueError as e:
        return Response(content=str(e), media_type="text/plain", status_code=500)
    metadata_dict = rocrate.metadata.generate()

    return metadata_dict
