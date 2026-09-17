import json

import jwt
import requests
from jwt import PyJWKClient

from app.argo.models import Workflow
from app.exceptions import (
    AuthenticationError,
    WorkflowNotFoundError,
    WorkflowParsingError,
)
from app.workflow_engines.base import WorkflowEngine


class LifeWatchEngine(WorkflowEngine):
    def __init__(
        self,
        *,
        keycloak_issuer: str,
        base_url: str,
        annotations_prefix: str,
        labels_prefix: str,
    ):
        self.name = "lifewatch"
        self.keycloak_issuer = keycloak_issuer
        self.base_url = base_url
        self.annotations_prefix = annotations_prefix
        self.labels_prefix = labels_prefix
        self.jwks_client = PyJWKClient(
            f"{self.keycloak_issuer}/protocol/openid-connect/certs"
        )

    def authenticate(self, token: str) -> None:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.keycloak_issuer,
                audience="account",
            )

        except jwt.PyJWTError as e:
            raise AuthenticationError("Invalid LifeWatch access token") from e

    def get_workflow(self, workflow_id: str, token: str) -> dict:

        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(
            f"{self.base_url}/{workflow_id}/status", headers=headers
        )
        response.raise_for_status()

        return response.json()

    def post_workflow(self, workflow_data: dict, token: str):
        pass
