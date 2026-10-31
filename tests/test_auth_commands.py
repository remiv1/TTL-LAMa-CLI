"""Tests des commandes d’authentification."""

from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands import auth as auth_commands
from ttlama_cli.exc import APIError, AuthenticationError, TokenStorageError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


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
    assert "Connexion réussie" in result.output
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
    monkeypatch.setattr(auth_commands, "get_access_token", lambda *_: "access-token")
    monkeypatch.setattr(auth_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["auth", "password-chg"],
        input=f"{current_password}\n{new_password}\n{new_password}\n",
    )

    assert result.exit_code == 0
    assert "Reconnectez-vous" in result.output
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
    monkeypatch.setattr(auth_commands, "get_access_token", lambda *_: "access-token")
    monkeypatch.setattr(auth_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["auth", "password-chg"],
        input="old-password\nnew-password\ndifferent-password\n",
    )

    assert result.exit_code == 1
    assert "ne correspondent pas" in result.output
    assert "old-password" not in result.output
    assert "new-password" not in result.output
    request_api.assert_not_called()
