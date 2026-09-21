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

    def health_check(self):
        pass

    def get_workflow(self, workflow_id: str, token: str) -> Workflow:

        headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}

        response = requests.get(
            f"{self.base_url}/{workflow_id}/status", headers=headers
        )
        if response.status_code == 404:
            raise WorkflowNotFoundError(f"Workflow with ID {workflow_id} not found")
        response.raise_for_status()
        try:
            wfl = self.parse_workflow(response.json())
        except KeyError as e:
            raise WorkflowParsingError(
                f"Failed to parse workflow with ID {workflow_id}, missing key: {e.args[0]}"
            ) from e

        return wfl

    def submit_workflow(self, workflow: Workflow, token: str) -> str:

        if not workflow.spec.arguments or not workflow.spec.arguments.parameters:
            parameters = []
        else:
            parameters = [
                param.model_dump() for param in workflow.spec.arguments.parameters
            ]

        workflow_template_ref = workflow.spec.workflowTemplateRef
        if not workflow_template_ref:
            raise WorkflowParsingError(
                "Failed to submit workflow to LifeWatch, workflow template reference is required"
            )

        payload = {
            "parameters": parameters,
            "workflow_template_ref": {"name": "bmd-terrestrial-sdm"},
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self.base_url + "/submit/from_template",
            headers=headers,
            data=json.dumps(payload),
        )
        response.raise_for_status()
        workflow_id = response.json().get("name")
        return workflow_id
