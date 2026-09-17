import requests

from app.exceptions import AuthenticationError
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
        if token != "correct-token":
            raise AuthenticationError("Invalid token for LifeWatchEngine")

    def get_workflow(self, workflow_id: str, token: str) -> dict:

        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(
            f"{self.base_url}/{workflow_id}/status", headers=headers
        )
        response.raise_for_status()

        return response.json()

    def post_workflow(self, workflow_data: dict, token: str):
        pass
