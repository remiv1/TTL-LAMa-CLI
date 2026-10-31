"""Tests des commandes d’authentification."""

from collections.abc import Callable
from unittest.mock import Mock
import json

import pytest
import yaml
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands import auth as auth_commands
from ttlama_cli.exc import APIError, AuthenticationError, TokenStorageError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


def _get_access_token_returning(token: str | None) -> Callable[[str, int], str | None]:
    def get_access_token(_server_url: str, _server_port: int) -> str | None:
        return token

    return get_access_token


def test_internal_login_saves_token_without_printing_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la commande enregistre le jeton sans afficher les secrets."""
    token = "secret-access-token"
    password = "secret-password"
    save_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "authenticate_internal",
        Mock(return_value=token),
    )
    monkeypatch.setattr(auth_commands, "save_access_token", save_token)

    result = CliRunner().invoke(
        app,
        ["auth", "login", "internal", "--user", "admin"],
        input=f"{password}\n",
    )

    assert result.exit_code == 0
    assert "Login successful" in result.output
    assert password not in result.output
    assert token not in result.output
    save_token.assert_called_once_with(
        "https://server.example",
        8443,
        token,
    )


def test_internal_login_shows_authentication_error_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la commande affiche une erreur d’authentification sans traceback."""
    save_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "authenticate_internal",
        Mock(side_effect=AuthenticationError("Identifiants incorrects.")),
    )
    monkeypatch.setattr(auth_commands, "save_access_token", save_token)

    result = CliRunner().invoke(
        app,
        ["auth", "login", "internal", "--user", "admin"],
        input="wrong-password\n",
    )

    assert result.exit_code == 1
    assert "Identifiants incorrects." in result.output
    assert "Traceback" not in result.output
    assert "wrong-password" not in result.output
    save_token.assert_not_called()


def test_internal_login_shows_api_error_without_saving_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la commande affiche une erreur d’API sans enregistrer le jeton."""
    save_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "authenticate_internal",
        Mock(side_effect=APIError("Serveur indisponible.")),
    )
    monkeypatch.setattr(auth_commands, "save_access_token", save_token)

    result = CliRunner().invoke(
        app,
        ["auth", "login", "internal", "--user", "admin"],
        input="password\n",
    )

    assert result.exit_code == 1
    assert "Serveur indisponible." in result.output
    assert "Traceback" not in result.output
    save_token.assert_not_called()


def test_internal_login_shows_token_storage_error_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la commande affiche une erreur de stockage du jeton sans traceback."""
    token = "secret-access-token"
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "authenticate_internal",
        Mock(return_value=token),
    )
    monkeypatch.setattr(
        auth_commands,
        "save_access_token",
        Mock(side_effect=TokenStorageError("Trousseau indisponible.")),
    )

    result = CliRunner().invoke(
        app,
        ["auth", "login", "internal", "--user", "admin"],
        input="password\n",
    )

    assert result.exit_code == 1
    assert "Trousseau indisponible." in result.output
    assert "Traceback" not in result.output
    assert token not in result.output


def test_password_change_sends_patch_without_displaying_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The password change uses hidden prompts and sends one authenticated PATCH."""
    current_password = "old-secret-password"
    new_password = "new-secret-password"
    request_api = Mock(return_value=None)
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning("access-token"),
    )
    monkeypatch.setattr(auth_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["auth", "password-chg"],
        input=f"{current_password}\n{new_password}\n{new_password}\n",
    )

    assert result.exit_code == 0
    assert "assword" in result.output
    assert current_password not in result.output
    assert new_password not in result.output
    assert "access-token" not in result.output
    request = request_api.call_args.args[2]
    assert isinstance(request, SpecificRequest)
    assert request.method is HTTPMethod.PATCH
    assert request.endpoint == "users/me/password"
    assert request.json_body == {
        "current_password": current_password,
        "new_password": new_password,
    }


def test_password_change_rejects_mismatched_confirmation_without_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Different new-password prompts are rejected before contacting the API."""
    request_api = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning("access-token"),
    )
    monkeypatch.setattr(auth_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["auth", "password-chg"],
        input="old-password\nnew-password\ndifferent-password\n",
    )

    assert result.exit_code == 1
    assert "do not match" in result.output
    assert "old-password" not in result.output
    assert "new-password" not in result.output
    request_api.assert_not_called()


def test_logout_without_local_token_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Logout succeeds without contacting the server when no token is stored."""
    request_api = Mock()
    delete_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning(None),
    )
    monkeypatch.setattr(auth_commands, "request_api", request_api)
    monkeypatch.setattr(auth_commands, "delete_access_token", delete_token)

    result = CliRunner().invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert "Already logged out" in result.output
    request_api.assert_not_called()
    delete_token.assert_not_called()


def test_logout_revokes_server_session_then_deletes_local_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Logout revokes the current session and removes its keyring entry."""
    request_api = Mock(return_value=None)
    delete_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning("access-token"),
    )
    monkeypatch.setattr(auth_commands, "request_api", request_api)
    monkeypatch.setattr(auth_commands, "delete_access_token", delete_token)

    result = CliRunner().invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert "Logout successful" in result.output
    specific_request = request_api.call_args.kwargs["specific_request"]
    assert specific_request.endpoint == "auth/logout"
    assert specific_request.method is HTTPMethod.POST
    delete_token.assert_called_once_with("https://server.example", 8443)


def test_logout_cleans_local_token_when_server_rejects_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 401 makes logout clean the stale local token and succeed idempotently."""
    delete_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning("stale-token"),
    )
    monkeypatch.setattr(
        auth_commands,
        "request_api",
        Mock(side_effect=AuthenticationError("Bearer token is invalid.")),
    )
    monkeypatch.setattr(auth_commands, "delete_access_token", delete_token)

    result = CliRunner().invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert "session was already inactive" in result.output
    delete_token.assert_called_once_with("https://server.example", 8443)


def test_logout_keeps_local_token_when_server_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A server error leaves the local token available for a later retry."""
    delete_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning("access-token"),
    )
    monkeypatch.setattr(
        auth_commands,
        "request_api",
        Mock(side_effect=APIError("Serveur indisponible.")),
    )
    monkeypatch.setattr(auth_commands, "delete_access_token", delete_token)

    result = CliRunner().invoke(app, ["auth", "logout"])

    assert result.exit_code == 1
    assert "Serveur indisponible" in result.output
    delete_token.assert_not_called()


def test_status_without_token_is_informative_or_checkable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disconnected status exits successfully unless check-connected is requested."""
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning(None),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "status"])
    checked = runner.invoke(app, ["auth", "status", "--check-connected"])

    assert result.exit_code == 0
    assert "inactive" in result.output
    assert checked.exit_code == 1


@pytest.mark.parametrize("output_flag", ["--json", "--yaml"])
def test_status_outputs_identity_and_session_expirations(
    monkeypatch: pytest.MonkeyPatch,
    output_flag: str,
) -> None:
    """Status shows the allowlisted identity and expiration-only session data."""
    response = {
        "user": {
            "id": "user-123",
            "username": "alice",
            "email": "alice@example.test",
            "is_admin": False,
            "token_hash": "must-not-be-shown",
        },
        "sessions": [
            {"expires_at": "2026-10-31T12:00:00+00:00", "token_hash": "secret"},
        ],
    }
    request_api = Mock(return_value=response)
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning("access-token"),
    )
    monkeypatch.setattr(auth_commands, "request_api", request_api)

    result = CliRunner().invoke(app, ["auth", "status", output_flag])

    assert result.exit_code == 0
    assert "must-not-be-shown" not in result.output
    assert "token_hash" not in result.output
    if output_flag == "--json":
        payload = json.loads(result.output)
    else:
        payload = yaml.safe_load(result.output)
    assert payload["session"] == "active"
    assert payload["user"]["username"] == "alice"
    assert payload["sessions"] == [{"expires_at": "2026-10-31T12:00:00+00:00"}]


def test_status_does_not_delete_a_rejected_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Status reports an invalid token without silently removing it."""
    delete_token = Mock()
    monkeypatch.setattr(
        auth_commands,
        "load_server_config",
        lambda: ("https://server.example", 8443),
    )
    monkeypatch.setattr(
        auth_commands,
        "get_access_token",
        _get_access_token_returning("stale-token"),
    )
    monkeypatch.setattr(
        auth_commands,
        "request_api",
        Mock(side_effect=AuthenticationError("Bearer token is invalid.")),
    )
    monkeypatch.setattr(auth_commands, "delete_access_token", delete_token)

    result = CliRunner().invoke(app, ["auth", "status"])

    assert result.exit_code == 1
    assert "Login again" in result.output
    delete_token.assert_not_called()
