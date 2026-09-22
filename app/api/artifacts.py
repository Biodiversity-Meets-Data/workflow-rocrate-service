from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.api.dependencies import check_auth, get_engine
from app.workflow_engines.base import WorkflowEngine

router = APIRouter(prefix="/workflow-engines/{engine}/artifacts", tags=["artifacts"])


@router.get(
    "/{artifact_key:path}",
)
def get_artifact(
    engine: str,
    artifact_key: str,
    wfl_engine: WorkflowEngine = Depends(get_engine),
    token: str = Depends(check_auth),
):
    url = wfl_engine.get_artifact_download_url(artifact_key)
    return RedirectResponse(url=url)
