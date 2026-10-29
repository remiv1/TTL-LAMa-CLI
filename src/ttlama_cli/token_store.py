"""Token storage for TTL-LAMa CLI.

This module provides functions to store and retrieve authentication tokens securely.


.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import keyring
from keyring.errors import KeyringError

from .exc import TokenStorageError

_SERVICE_NAME = "ttlama_cli"


def _service(server_url: str, server_port: int) -> str:
    return f"{_SERVICE_NAME}:{server_url.rstrip('/')}:{server_port}"

def save_access_token(
        server_url: str,
        server_port: int,
        username: str,
        token: str,
) -> None:
    """Save the access token for the given server and user."""
    try:
        keyring.set_password(
            _service(server_url, server_port),
            username,
            token,
        )
    except KeyringError as error:
        raise TokenStorageError(
            "Impossible d’enregistrer le jeton dans le trousseau système."
        ) from error

def get_access_token(
    server_url: str,
    server_port: int,
    username: str,
) -> str | None:
    """Retrieve the access token for the given server and user."""
    return keyring.get_password(
        _service(server_url, server_port),
        username,
    )

def delete_access_token(
    server_url: str,
    server_port: int,
    username: str,
) -> None:
    """Delete the access token for the given server and user."""
    service = _service(server_url, server_port)
    if keyring.get_password(service, username) is not None:
        keyring.delete_password(
            service,
            username,
        )

