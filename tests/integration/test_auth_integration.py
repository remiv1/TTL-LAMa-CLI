"""Tests d’authentification de la CLI contre une instance réelle."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from ttlama_cli import token_store
from ttlama_cli.cli import app

_REQUIRED_ENVIRONMENT = (
    "TTLAMA_TEST_SERVER_URL",
    "TTLAMA_TEST_SERVER_PORT",
    "TTLAMA_TEST_ADMIN_USERNAME",
    "TTLAMA_TEST_ADMIN_PASSWORD",
)
pytestmark = pytest.mark.skipif(
    not all(os.environ.get(name) for name in _REQUIRED_ENVIRONMENT),
    reason="Les tests d’intégration nécessitent leur environnement Compose.",
)


@pytest.fixture
def memory_keyring(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[str, str], str]:
    """Remplacer le trousseau du système par un stockage mémoire isolé."""
    tokens: dict[tuple[str, str], str] = {}

    def set_password(service: str, username: str, password: str) -> None:
        tokens[(service, username)] = password

    def get_password(service: str, username: str) -> str | None:
        return tokens.get((service, username))

    monkeypatch.setattr(token_store.keyring, "set_password", set_password)
    monkeypatch.setattr(token_store.keyring, "get_password", get_password)
    monkeypatch.setattr(token_store.keyring, "delete_password", Mock())
    return tokens


@pytest.fixture
def server_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[str, int, str, str]:
    """Configurer la CLI pour le serveur éphémère et un dossier XDG temporaire."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return (
        os.environ["TTLAMA_TEST_SERVER_URL"],
        int(os.environ["TTLAMA_TEST_SERVER_PORT"]),
        os.environ["TTLAMA_TEST_ADMIN_USERNAME"],
        os.environ["TTLAMA_TEST_ADMIN_PASSWORD"],
    )


def configure_server(url: str, port: int) -> None:
    """Enregistrer l’URL et le port du serveur via la commande publique."""
    result = CliRunner().invoke(
        app,
        ["config", "set-server", url, "--port", str(port)],
    )
    assert result.exit_code == 0, result.output


def test_internal_login_against_server_saves_token(
    memory_keyring: dict[tuple[str, str], str], # pylint: disable=W0621
    server_config: tuple[str, int, str, str],   # pylint: disable=W0621
) -> None:
    """Un login réel enregistre le jeton sans l’afficher."""
    server_url, server_port, username, password = server_config
    configure_server(server_url, server_port)

    result = CliRunner().invoke(
        app,
        ["auth", "login", "internal", "--user", username],
        input=f"{password}\n",
    )

    assert result.exit_code == 0, result.output
    assert "Connexion réussie" in result.output
    assert password not in result.output

    token = token_store.get_access_token(server_url, server_port, username)
    assert token
    assert token not in result.output
    assert memory_keyring


def test_internal_login_against_server_rejects_bad_password(
    memory_keyring: dict[tuple[str, str], str], # pylint: disable=W0621
    server_config: tuple[str, int, str, str],   # pylint: disable=W0621
) -> None:
    """Un mauvais mot de passe échoue proprement sans stocker de jeton."""
    server_url, server_port, username, _ = server_config
    configure_server(server_url, server_port)
    wrong_password = "invalid-integration-password"

    result = CliRunner().invoke(
        app,
        ["auth", "login", "internal", "--user", username],
        input=f"{wrong_password}\n",
    )

    assert result.exit_code == 1
    assert "incorrect" in result.output.lower()
    assert "Traceback" not in result.output
    assert wrong_password not in result.output
    assert token_store.get_access_token(server_url, server_port, username) is None
    assert memory_keyring == {}
