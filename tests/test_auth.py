import pytest

from app.auth import (
    KeycloakJWTAuthProvider,
    StaticTokenAuthProvider,
)
from app.exceptions import AuthenticationError


def test_static_token_provider_accepts_correct_token():
    provider = StaticTokenAuthProvider(token="expected-token")
    assert provider.authenticate("expected-token") == "expected-token"


def test_static_token_provider_rejects_missing_or_invalid_token():
    provider = StaticTokenAuthProvider(token="expected-token")

    with pytest.raises(AuthenticationError):
        provider.authenticate(None)

    with pytest.raises(AuthenticationError):
        provider.authenticate("wrong-token")


def test_static_token_provider_reads_from_environment(monkeypatch):
    monkeypatch.setenv("WORKFLOW_API_TOKEN", "env-token")

    provider = StaticTokenAuthProvider.from_value_or_env(token_env="WORKFLOW_API_TOKEN")
    assert provider.authenticate("env-token") == "env-token"


def test_static_token_provider_requires_existing_env_var(monkeypatch):
    monkeypatch.delenv("WORKFLOW_API_TOKEN", raising=False)

    with pytest.raises(ValueError):
        StaticTokenAuthProvider.from_value_or_env(token_env="WORKFLOW_API_TOKEN")


def test_keycloak_provider_requires_token():
    provider = KeycloakJWTAuthProvider(issuer="https://issuer.example.org")

    with pytest.raises(AuthenticationError):
        provider.authenticate(None)


def test_keycloak_provider_uses_configured_audience_and_issuer(monkeypatch):
    class FakeJWK:
        key = "public-key"

    class FakeJWKClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            assert token == "jwt-token"
            return FakeJWK()

    captured = {}

    def fake_decode(token, **kwargs):
        captured["token"] = token
        captured["kwargs"] = kwargs
        return {}

    monkeypatch.setattr("app.auth.PyJWKClient", FakeJWKClient)
    monkeypatch.setattr("app.auth.jwt.decode", fake_decode)

    provider = KeycloakJWTAuthProvider(
        issuer="https://issuer.example.org/realm/test",
        audience="account",
    )

    assert provider.authenticate("jwt-token") == "jwt-token"
    assert captured["token"] == "jwt-token"
    assert captured["kwargs"]["issuer"] == "https://issuer.example.org/realm/test"
    assert captured["kwargs"]["audience"] == "account"


def test_keycloak_provider_can_skip_audience_check(monkeypatch):
    class FakeJWK:
        key = "public-key"

    class FakeJWKClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            return FakeJWK()

    captured = {}

    def fake_decode(token, **kwargs):
        captured["kwargs"] = kwargs
        return {}

    monkeypatch.setattr("app.auth.PyJWKClient", FakeJWKClient)
    monkeypatch.setattr("app.auth.jwt.decode", fake_decode)

    provider = KeycloakJWTAuthProvider(
        issuer="https://issuer.example.org/realm/test",
        audience=None,
    )

    provider.authenticate("jwt-token")
    assert "audience" not in captured["kwargs"]
