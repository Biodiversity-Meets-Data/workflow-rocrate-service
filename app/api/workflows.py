import yaml
from fastapi import APIRouter, Response

from app.argo import reconstruct_template, reconstruct_workflow
from app.rocrate import generate_WROC_from_workflow, generate_WRROC_from_workflow
from app.workflow_engines.base import WorkflowEngine
from app.workflow_engines.dummy_engine import DummyEngine
from app.workflow_engines.lifewatch_engine import LifeWatchEngine

router = APIRouter(prefix="/workflow-engines/{engine}/workflows", tags=["workflows"])

engines: dict[str, WorkflowEngine] = {
    "lifewatch": LifeWatchEngine(),
    "dummy": DummyEngine(),
}


def get_engine(name: str) -> WorkflowEngine:
    try:
        return engines[name]
    except KeyError:
        raise ValueError(f"Unknown workflow engine: {name}")


@router.get("/{workflow_id}/workflow.yaml")
def get_workflow(engine: str, workflow_id: str):
    try:
        wfl_engine = get_engine(engine)
    except ValueError as e:
        return Response(
            content=str(e),
            media_type="text/plain",
            status_code=400,
        )

    wfl = wfl_engine.get_workflow(workflow_id, token="fake-token")
    wfl = reconstruct_workflow(wfl, wfl_engine.annotations_prefix)
    wfl = yaml.safe_dump(wfl, sort_keys=False)

    return Response(
        content=wfl,
        media_type="application/yaml",
        headers={"Content-Disposition": "attachment; filename=workflow.yaml"},
    )


@router.get("/{workflow_id}/template.yaml")
def get_template(engine: str, workflow_id: str):
    try:
        wfl_engine = get_engine(engine)
    except ValueError as e:
        return Response(
            content=str(e),
            media_type="text/plain",
            status_code=400,
        )

    wfl = wfl_engine.get_workflow(workflow_id, token="fake-token")
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


@router.get(
    "/{workflow_id}/metadata",
    description="Get the RO-Crate metadata for a workflow in JSON format. The profile parameter can be either 'WROC' or 'WRROC'.",
)
def get_metadata(engine: str, workflow_id: str, profile: str = "WROC"):
    try:
        wfl_engine = get_engine(engine)
    except ValueError as e:
        return Response(
            content=str(e),
            media_type="text/plain",
            status_code=400,
        )

    wfl = wfl_engine.get_workflow(workflow_id, token="fake-token")

    try:
        if profile == "WROC":
            rocrate = generate_WROC_from_workflow(
                wfl, prefix=wfl_engine.annotations_prefix, base_url=wfl_engine.base_url
            )
        elif profile == "WRROC":
            rocrate = generate_WRROC_from_workflow(
                wfl, prefix=wfl_engine.annotations_prefix, base_url=wfl_engine.base_url
            )
        else:
            return Response(
                content=f"Unknown profile: {profile}",
                media_type="text/plain",
                status_code=400,
            )
    except ValueError as e:
        return Response(content=str(e), media_type="text/plain", status_code=500)
    metadata_dict = rocrate.metadata.generate()

    return metadata_dict
