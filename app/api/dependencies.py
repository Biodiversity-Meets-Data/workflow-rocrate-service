from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import AuthProvider
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


def get_auth_provider(engine: str) -> AuthProvider:
    try:
        auth_provider = settings.authenticators[engine]
    except KeyError:
        raise HTTPException(
            detail=f"Unknown workflow engine: {engine}",
            status_code=404,
        )
    return auth_provider


bearer_scheme = HTTPBearer(auto_error=False)


def check_auth(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    auth_provider: AuthProvider = Depends(get_auth_provider),
) -> str:
    try:
        token = credentials.credentials if credentials else None
        return auth_provider.authenticate(token=token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )
