"""Tests du stockage des jetons."""

import pytest
from keyring.errors import KeyringError

from ttlama_cli import token_store
from ttlama_cli.exc import TokenStorageError


def test_save_access_token_wraps_keyring_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la fonction enveloppe les erreurs de Keyring dans TokenStorageError."""
    def fail_to_save(*_args: object) -> None:
        raise KeyringError("backend unavailable")

    monkeypatch.setattr(token_store.keyring, "set_password", fail_to_save)

    with pytest.raises(TokenStorageError, match="trousseau système"):
        token_store.save_access_token(
            "https://server.example",
            8443,
            "secret-access-token",
        )

def test_save_access_token_replaces_existing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new token replaces the one already stored for this instance."""
    stored_tokens: dict[tuple[str, str], str] = {}

    def set_password(service: str, account: str, token: str) -> None:
        stored_tokens[(service, account)] = token

    def get_password(service: str, account: str) -> str | None:
        return stored_tokens.get((service, account))

    monkeypatch.setattr(token_store.keyring, "set_password", set_password)
    monkeypatch.setattr(token_store.keyring, "get_password", get_password)

    server_url = "https://server.example"
    server_port = 8443

    token_store.save_access_token(server_url, server_port, "first-token")
    token_store.save_access_token(server_url, server_port, "second-token")

    assert token_store.get_access_token(server_url, server_port) == "second-token"
    assert len(stored_tokens) == 1
