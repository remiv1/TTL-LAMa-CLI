"""API client for TTL-LAMa CLI.

This module provides functions to interact with the TTL-LAMa server API.

.. functions::
    - `authenticate_internal`: Authenticate with the TTL-LAMa server and return an authentication
    token.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from typing import cast

from requests import Session, request
from requests.exceptions import RequestException

from .exc import APIError, AuthenticationError, AuthorizationError
from .objects import ServerParameters, SpecificRequest


def authenticate_internal(server_url: str, server_port: int, username: str, password: str) -> str:
    """Authenticate with the TTL-LAMa server and return an authentication token.
    
    :param server_url: URL of the TTL-LAMa server.
    :type server_url: str
    :param server_port: Port of the TTL-LAMa server.
    :type server_port: int
    :param username: Username for authentication.
    :type username: str
    :param password: Password for authentication.
    :type password: str
    :return: Authentication token.
    :rtype: str
    :raises APIError: If there is an API error.
    :raises AuthenticationError: If authentication fails.
    :raises AuthorizationError: If the user does not have admin privileges.
    """
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

def request_api(
        server: ServerParameters,
        token: str,
        specific_request: SpecificRequest,
    ) -> dict[str, object] | list[dict[str, object]] | None:
    """Request the API.

    :param server: Server parameters.
    :type server: ServerParameters
    :param token: Authentication token.
    :type token: str
    :param specific_request: Specific HTTP request details.
    :type specific_request: SpecificRequest
    :return: An object, a list of objects, or None if the API returned no data.
    :rtype: dict[str, object] | list[dict[str, object]] | None
    :raises APIError: If there is an API error.
    """
    url = f"{server.server_url}:{server.server_port}/api/v1/{specific_request.endpoint}"
    try:
        response = request(
            specific_request.method,
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=specific_request.params,
            json=specific_request.json_body,
            timeout=5,
        )
    except RequestException as error:
        raise APIError("Impossible de joindre l’API TTL-LAMa.") from error

    if response.status_code == 401:
        raise AuthenticationError("Bearer token is invalid.")
    if response.status_code == 403:
        raise AuthorizationError("You haven't admin privileges.")

    try:
        response.raise_for_status()
    except RequestException as error:
        raise APIError(
            f"TTL-LAMa API responded with HTTP status {response.status_code}."
        ) from error

    if response.status_code == 204:
        return None

    try:
        return response.json()
    except ValueError as error:
        raise APIError("API response is invalid.") from error
