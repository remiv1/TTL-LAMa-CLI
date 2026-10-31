"""Token storage for TTL-LAMa CLI.

This module provides functions to store and retrieve authentication tokens securely.

.. functions::
    - `save_access_token`: Save the access token for the given server and user.
    - `get_access_token`: Retrieve the access token for the given server and user.
    - `delete_access_token`: Delete the access token for the given server and user.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import keyring
from keyring.errors import KeyringError

from .exc import TokenStorageError

_SERVICE_NAME = "ttlama_cli"
_TOKEN_ACCOUNT = "current"

def _service(server_url: str, server_port: int) -> str:
    return f"{_SERVICE_NAME}:{server_url.rstrip('/')}:{server_port}"

def save_access_token(server_url: str, server_port: int, token: str) -> None:
    """Save the access token for the given server and user.

    :param server_url: URL of the server.
    :type server_url: str
    :param server_port: Port of the server.
    :type server_port: int
    :param token: The access token to save.
    :type token: str
    """
    try:
        keyring.set_password(
            _service(server_url, server_port),
            _TOKEN_ACCOUNT,
            token,
        )
    except KeyringError as error:
        raise TokenStorageError(
            "Impossible d’enregistrer le jeton dans le trousseau système."
        ) from error

def get_access_token(server_url: str, server_port: int) -> str | None:
    """Retrieve the access token for the given server and user.
    
    :param server_url: URL of the server.
    :type server_url: str
    :param server_port: Port of the server.
    :type server_port: int
    :return: The access token if it exists, otherwise None.
    :rtype: str | None
    """
    try:
        return keyring.get_password(
            _service(server_url, server_port),
            _TOKEN_ACCOUNT,
        )
    except KeyringError as error:
        raise TokenStorageError(
            "Impossible de lire le jeton dans le trousseau système."
        ) from error

def delete_access_token(server_url: str, server_port: int) -> None:
    """Delete the access token for the given server and user.
    
    :param server_url: URL of the server.
    :type server_url: str
    :param server_port: Port of the server.
    :type server_port: int
    """
    service = _service(server_url, server_port)
    try:
        if keyring.get_password(service, _TOKEN_ACCOUNT) is not None:
            keyring.delete_password(
                service,
                _TOKEN_ACCOUNT,
            )
    except KeyringError as error:
        raise TokenStorageError(
            "Impossible de supprimer le jeton du trousseau système."
        ) from error
