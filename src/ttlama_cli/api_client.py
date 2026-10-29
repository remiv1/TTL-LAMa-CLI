"""API client for TTL-LAMa CLI.

This module provides functions to interact with the TTL-LAMa server API.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from typing import cast

from requests import Session
from requests.exceptions import RequestException

from .exc import APIError, AuthenticationError


def authenticate_internal(server_url: str, server_port: int, username: str, password: str) -> str:
    """Authenticate with the TTL-LAMa server and return an authentication token."""
    session = Session()

    try:
        csrf_response = session.get(
            f"{server_url}:{server_port}/api/v1/csrf",
            timeout=5,
        )
        csrf_response.raise_for_status()
        csrf_data = csrf_response.json()
        if not isinstance(csrf_data, dict):
            raise APIError("La réponse CSRF de l’API est invalide.")

        csrf_payload = cast(dict[str, object], csrf_data)
        csrf = csrf_payload.get("csrf_token")
        if not isinstance(csrf, str) or not csrf:
            raise APIError("La réponse CSRF de l’API ne contient pas de jeton.")

        response = session.post(
            f"{server_url}:{server_port}/api/v1/auth",
            json={"username": username, "password": password},
            headers={"X-CSRFToken": csrf},
            timeout=5,
        )
    except RequestException as error:
        raise APIError("Impossible de joindre l’API TTL-LAMa.") from error

    if response.status_code == 401:
        raise AuthenticationError("Nom d’utilisateur ou mot de passe incorrect.")
    if response.status_code == 501:
        raise APIError("L’authentification interne n’est pas disponible sur ce serveur.")

    try:
        response.raise_for_status()
    except RequestException as error:
        raise APIError(
            f"L’API TTL-LAMa a répondu avec le statut HTTP {response.status_code}."
        ) from error

    try:
        response_data = response.json()
    except ValueError as error:
        raise APIError("La réponse d’authentification de l’API est invalide.") from error

    if not isinstance(response_data, dict):
        raise APIError("La réponse d’authentification de l’API est invalide.")

    payload = cast(dict[str, object], response_data)
    token = payload.get("access_token")

    if not isinstance(token, str) or not token:
        raise APIError("La réponse d’authentification ne contient pas de jeton valide.")
    return token
