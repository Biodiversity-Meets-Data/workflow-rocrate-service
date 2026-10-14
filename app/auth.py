import os
from abc import ABC, abstractmethod

import jwt
from jwt import PyJWKClient

from app.exceptions import AuthenticationError


class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, token: str | None) -> str:
        pass


class StaticTokenAuthProvider(AuthProvider):
    def __init__(self, *, token: str):
        self._token = token

    @classmethod
    def from_value_or_env(
        cls,
        *,
        token: str | None = None,
        token_env: str | None = None,
    ) -> "StaticTokenAuthProvider":
        if token:
            return cls(token=token)

        if token_env:
            env_token = os.getenv(token_env)
            if not env_token:
                raise ValueError(
                    f"Missing environment variable '{token_env}' required for static token auth"
                )
            return cls(token=env_token)

        raise ValueError("Static token auth requires either token or token_env")

    def authenticate(self, token: str | None) -> str:
        if not token:
            raise AuthenticationError("Bearer token is required")
        if token != self._token:
            raise AuthenticationError("Invalid bearer token")
        return token


class KeycloakJWTAuthProvider(AuthProvider):
    def __init__(
        self,
        *,
        issuer: str,
        audience: str | None = "account",
        algorithms: list[str] | None = None,
        jwks_url: str | None = None,
    ):
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms or ["RS256"]
        self.jwks_url = jwks_url or f"{self.issuer}/protocol/openid-connect/certs"
        self.jwks_client: PyJWKClient | None = None

    def authenticate(self, token: str | None) -> str:
        if not token:
            raise AuthenticationError("Bearer token is required")

        try:
            if self.jwks_client is None:
                self.jwks_client = PyJWKClient(self.jwks_url)
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            decode_kwargs = {
                "key": signing_key.key,
                "algorithms": self.algorithms,
                "issuer": self.issuer,
            }
            if self.audience is not None:
                decode_kwargs["audience"] = self.audience

            jwt.decode(
                token,
                **decode_kwargs,
            )
        except jwt.PyJWTError as e:
            raise AuthenticationError("Invalid access token", e.args[0]) from e

        return token
