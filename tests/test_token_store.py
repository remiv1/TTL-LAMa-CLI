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
            "admin",
            "secret-access-token",
        )
