import json
import tempfile
from pathlib import Path
from typing import Annotated, Literal

import yaml
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from app.api.dependencies import check_auth, get_engine
from app.argo.argo2roc import generate_WROC_from_workflow, generate_WRROC_from_workflow
from app.argo.reconstruction import (
    reconstruct_template,
    reconstruct_workflow,
    reconstruct_workflow_run,
)
from app.argo.roc2argo import generate_workflow_from_rocrate
from app.rocrate_io import get_crate_workflow_from_zip
from app.workflow_engines.base import WorkflowEngine

router = APIRouter(prefix="/workflow-engines/{engine}/workflows", tags=["workflows"])


@router.get("/{workflow_id}/workflow.yaml")
def get_workflow(
    engine: str,
    workflow_id: str,
    wfl_engine: WorkflowEngine = Depends(get_engine),
    token: str = Depends(check_auth),
):
    wfl = wfl_engine.get_workflow(workflow_id, token=token)
    wfl = reconstruct_workflow(wfl, wfl_engine)
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


@router.get(
    "/{workflow_id}/rocrate",
    description="Get the RO-Crate for a workflow in ZIP format. ",
)
def get_rocrate(
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

    workflow_yaml = yaml.safe_dump(
        reconstruct_workflow(wfl, wfl_engine), sort_keys=False
    )
    workflow_file = Path(tempfile.mkdtemp()) / "workflow.yaml"
    workflow_file.write_text(workflow_yaml, encoding="utf-8")

    template_yaml = yaml.safe_dump(reconstruct_template(wfl), sort_keys=False)
    template_file = Path(tempfile.mkdtemp()) / "template.yaml"
    template_file.write_text(template_yaml, encoding="utf-8")

    try:
        if profile == "WROC":
            rocrate = generate_WROC_from_workflow(
                wfl,
                prefix=wfl_engine.annotations_prefix,
                base_url=wfl_engine.base_url,
                workflow_file=workflow_file,
                template_file=template_file,
                validate=validate_rocrate,
            )
        elif profile == "WRROC":
            workflow_run_yaml = yaml.safe_dump(
                reconstruct_workflow_run(wfl, wfl_engine), sort_keys=False
            )
            workflow_run_file = Path(tempfile.mkdtemp()) / "workflow-run.yaml"
            workflow_run_file.write_text(workflow_run_yaml, encoding="utf-8")
            rocrate = generate_WRROC_from_workflow(
                wfl,
                prefix=wfl_engine.annotations_prefix,
                base_url=wfl_engine.base_url,
                workflow_file=workflow_file,
                template_file=template_file,
                workflow_run_file=workflow_run_file,
                validate=validate_rocrate,
            )
    except ValueError as e:
        return Response(content=str(e), media_type="text/plain", status_code=500)

    return StreamingResponse(
        content=rocrate.stream_zip(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={wfl_engine}_{workflow_id}.zip"
        },
    )


@router.get(
    "/{workflow_id}/workflow-run.yaml",
)
def get_workflow_run(
    engine: str,
    workflow_id: str,
    wfl_engine: WorkflowEngine = Depends(get_engine),
    token: str = Depends(check_auth),
):

    wfl = wfl_engine.get_workflow(workflow_id, token=token)
    workflow_run = reconstruct_workflow_run(wfl, wfl_engine)

    if not workflow_run:
        return Response(
            content="No workflow run found for this workflow.",
            media_type="text/plain",
            status_code=404,
        )

    workflow_run = yaml.safe_dump(workflow_run, sort_keys=False)

    return Response(
        content=workflow_run,
        media_type="application/yaml",
        headers={"Content-Disposition": "attachment; filename=workflow-run.yaml"},
    )


@router.post(
    "",
    description="This is a placeholder endpoint for workflow submission. It is not implemented yet.",
)
async def submit_workflow(
    engine: str,
    rocrate_file: Annotated[
        UploadFile,
        File(description="Workflow RO-Crate .zip file containing the workflow"),
    ],
    workflow_parameters: Annotated[
        str,
        Form(
            description="Workflow parameters for the workflow",
            examples=[{"param1": "value1", "param2": "value2"}],
        ),
    ],
    wfl_engine: WorkflowEngine = Depends(get_engine),
    token: str = Depends(check_auth),
):
    parameters = json.loads(workflow_parameters)

    if not isinstance(parameters, dict):
        raise HTTPException(
            status_code=422,
            detail="workflow_parameters must be a JSON object",
        )
    crate, workflow = await get_crate_workflow_from_zip(rocrate_file)
    try:
        wfl = generate_workflow_from_rocrate(crate, workflow, parameters)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    workflow_id = wfl_engine.submit_workflow(wfl, token=token)
    return Response(
        content=json.dumps({"workflow_id": workflow_id}),
        media_type="application/json",
    )
