"""Tests des commandes d’authentification."""

from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands import auth as auth_commands
from ttlama_cli.exc import APIError, AuthenticationError, TokenStorageError


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
        "admin",
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
