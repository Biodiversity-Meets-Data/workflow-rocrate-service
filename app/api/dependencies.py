from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.exceptions import AuthenticationError
from app.settings import settings
from app.workflow_engines.base import WorkflowEngine


def get_engine(engine: str) -> WorkflowEngine:
    try:
        wfl_engine = settings.engines[engine]
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
