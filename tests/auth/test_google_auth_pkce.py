"""Regression tests for OAuth PKCE flow wiring and auth edge cases."""

import os
import sys
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from auth.google_auth import (  # noqa: E402
    _find_any_credentials,
    create_oauth_flow,
    load_client_secrets_from_env,
)
from auth.oauth_config import OAuthConfig  # noqa: E402


DUMMY_CLIENT_CONFIG = {
    "web": {
        "client_id": "dummy-client-id.apps.googleusercontent.com",
        "client_secret": "dummy-secret",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


def test_create_oauth_flow_autogenerates_verifier_when_missing():
    expected_flow = object()
    with (
        patch(
            "auth.google_auth.load_client_secrets_from_env",
            return_value=DUMMY_CLIENT_CONFIG,
        ),
        patch(
            "auth.google_auth.Flow.from_client_config",
            return_value=expected_flow,
        ) as mock_from_client_config,
    ):
        flow = create_oauth_flow(
            scopes=["openid"],
            redirect_uri="http://localhost/callback",
            state="oauth-state-1",
        )

    assert flow is expected_flow
    args, kwargs = mock_from_client_config.call_args
    assert args[0] == DUMMY_CLIENT_CONFIG
    assert kwargs["autogenerate_code_verifier"] is True
    assert "code_verifier" not in kwargs


def test_create_oauth_flow_preserves_callback_verifier():
    expected_flow = object()
    with (
        patch(
            "auth.google_auth.load_client_secrets_from_env",
            return_value=DUMMY_CLIENT_CONFIG,
        ),
        patch(
            "auth.google_auth.Flow.from_client_config",
            return_value=expected_flow,
        ) as mock_from_client_config,
    ):
        flow = create_oauth_flow(
            scopes=["openid"],
            redirect_uri="http://localhost/callback",
            state="oauth-state-2",
            code_verifier="saved-verifier",
        )

    assert flow is expected_flow
    args, kwargs = mock_from_client_config.call_args
    assert args[0] == DUMMY_CLIENT_CONFIG
    assert kwargs["code_verifier"] == "saved-verifier"
    assert kwargs["autogenerate_code_verifier"] is False


def test_create_oauth_flow_file_config_still_enables_pkce():
    expected_flow = object()
    with (
        patch("auth.google_auth.load_client_secrets_from_env", return_value=None),
        patch("auth.google_auth.os.path.exists", return_value=True),
        patch(
            "auth.google_auth.Flow.from_client_secrets_file",
            return_value=expected_flow,
        ) as mock_from_file,
    ):
        flow = create_oauth_flow(
            scopes=["openid"],
            redirect_uri="http://localhost/callback",
            state="oauth-state-3",
        )

    assert flow is expected_flow
    _args, kwargs = mock_from_file.call_args
    assert kwargs["autogenerate_code_verifier"] is True
    assert "code_verifier" not in kwargs


def test_create_oauth_flow_allows_disabling_autogenerate_without_verifier():
    expected_flow = object()
    with (
        patch(
            "auth.google_auth.load_client_secrets_from_env",
            return_value=DUMMY_CLIENT_CONFIG,
        ),
        patch(
            "auth.google_auth.Flow.from_client_config",
            return_value=expected_flow,
        ) as mock_from_client_config,
    ):
        flow = create_oauth_flow(
            scopes=["openid"],
            redirect_uri="http://localhost/callback",
            state="oauth-state-4",
            autogenerate_code_verifier=False,
        )

    assert flow is expected_flow
    _args, kwargs = mock_from_client_config.call_args
    assert kwargs["autogenerate_code_verifier"] is False
    assert "code_verifier" not in kwargs


def test_workspace_oauth_env_overrides_generic_env_in_client_loader():
    with patch.dict(
        os.environ,
        {
            "GOOGLE_OAUTH_CLIENT_ID": "generic-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "generic-client-secret",
            "GOOGLE_OAUTH_REDIRECT_URI": "https://generic.example/callback",
            "WORKSPACE_GOOGLE_OAUTH_CLIENT_ID": "workspace-client-id",
            "WORKSPACE_GOOGLE_OAUTH_CLIENT_SECRET": "workspace-client-secret",
            "WORKSPACE_GOOGLE_OAUTH_REDIRECT_URI": "https://workspace.example/callback",
        },
        clear=False,
    ):
        config = load_client_secrets_from_env()

    assert config is not None
    assert config["web"]["client_id"] == "workspace-client-id"
    assert config["web"]["client_secret"] == "workspace-client-secret"
    assert config["web"]["redirect_uris"] == ["https://workspace.example/callback"]


def test_workspace_oauth_env_overrides_generic_env_in_oauth_config():
    with patch.dict(
        os.environ,
        {
            "GOOGLE_OAUTH_CLIENT_ID": "generic-client-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "generic-client-secret",
            "GOOGLE_OAUTH_REDIRECT_URI": "https://generic.example/callback",
            "WORKSPACE_GOOGLE_OAUTH_CLIENT_ID": "workspace-client-id",
            "WORKSPACE_GOOGLE_OAUTH_CLIENT_SECRET": "workspace-client-secret",
            "WORKSPACE_GOOGLE_OAUTH_REDIRECT_URI": "https://workspace.example/callback",
        },
        clear=False,
    ):
        config = OAuthConfig()

    assert config.client_id == "workspace-client-id"
    assert config.client_secret == "workspace-client-secret"
    assert config.redirect_uri == "https://workspace.example/callback"


def test_find_any_credentials_prefers_requested_user():
    requested_creds = object()
    other_creds = object()

    class StubStore:
        def list_users(self):
            return ["kah411@pitt.edu", "klhakiman@gmail.com"]

        def get_credential(self, user_email):
            return {
                "kah411@pitt.edu": other_creds,
                "klhakiman@gmail.com": requested_creds,
            }.get(user_email)

    with patch("auth.google_auth.get_credential_store", return_value=StubStore()):
        credentials, user_email = _find_any_credentials(
            preferred_user_email="klhakiman@gmail.com"
        )

    assert credentials is requested_creds
    assert user_email == "klhakiman@gmail.com"


def test_find_any_credentials_falls_back_to_first_user_when_no_request():
    first_creds = object()

    class StubStore:
        def list_users(self):
            return ["kah411@pitt.edu", "klhakiman@gmail.com"]

        def get_credential(self, user_email):
            return {"kah411@pitt.edu": first_creds}.get(user_email)

    with patch("auth.google_auth.get_credential_store", return_value=StubStore()):
        credentials, user_email = _find_any_credentials()

    assert credentials is first_creds
    assert user_email == "kah411@pitt.edu"
