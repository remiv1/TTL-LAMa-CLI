"""Tests du client HTTP d’authentification."""

from unittest.mock import Mock

import pytest
from requests.exceptions import ConnectionError, HTTPError  # pylint: disable=W0622

from ttlama_cli import api_client
from ttlama_cli.exc import APIError, AuthenticationError


def test_authenticate_internal_returns_token_and_sends_csrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la fonction renvoie le jeton d'accès et envoie le jeton CSRF."""
    session = Mock()
    csrf_response = Mock()
    csrf_response.json.return_value = {"csrf_token": "csrf-value"}
    auth_response = Mock()
    auth_response.status_code = 200
    auth_response.json.return_value = {"access_token": "access-value"}
    session.get.return_value = csrf_response
    session.post.return_value = auth_response
    monkeypatch.setattr(api_client, "Session", lambda: session)

    token = api_client.authenticate_internal(
        "https://server.example",
        8443,
        "admin",
        "password",
    )

    assert token == "access-value"
    session.get.assert_called_once_with(
        "https://server.example:8443/api/v1/csrf",
        timeout=5,
    )
    session.post.assert_called_once_with(
        "https://server.example:8443/api/v1/auth",
        json={"username": "admin", "password": "password"},
        headers={"X-CSRFToken": "csrf-value"},
        timeout=5,
    )


def test_authenticate_internal_rejects_invalid_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la fonction rejette les identifiants invalides."""
    session = Mock()
    csrf_response = Mock()
    csrf_response.json.return_value = {"csrf_token": "csrf-value"}
    auth_response = Mock()
    auth_response.status_code = 401
    session.get.return_value = csrf_response
    session.post.return_value = auth_response
    monkeypatch.setattr(api_client, "Session", lambda: session)

    with pytest.raises(AuthenticationError, match="incorrect"):
        api_client.authenticate_internal(
            "https://server.example",
            8443,
            "admin",
            "wrong-password",
        )


def test_authenticate_internal_wraps_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la fonction enveloppe les erreurs de connexion."""
    session = Mock()
    session.get.side_effect = ConnectionError("connection refused")
    monkeypatch.setattr(api_client, "Session", lambda: session)

    with pytest.raises(APIError, match="Impossible de joindre"):
        api_client.authenticate_internal(
            "https://server.example",
            8443,
            "admin",
            "password",
        )


def test_authenticate_internal_wraps_unexpected_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la fonction enveloppe les erreurs HTTP inattendues."""
    session = Mock()
    csrf_response = Mock()
    csrf_response.json.return_value = {"csrf_token": "csrf-value"}
    auth_response = Mock()
    auth_response.status_code = 503
    auth_response.raise_for_status.side_effect = HTTPError("service unavailable")
    session.get.return_value = csrf_response
    session.post.return_value = auth_response
    monkeypatch.setattr(api_client, "Session", lambda: session)

    with pytest.raises(APIError, match="statut HTTP 503"):
        api_client.authenticate_internal(
            "https://server.example",
            8443,
            "admin",
            "password",
        )


def test_authenticate_internal_rejects_missing_csrf_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la fonction rejette l'absence de jeton CSRF."""
    session = Mock()
    csrf_response = Mock()
    csrf_response.json.return_value = {}
    session.get.return_value = csrf_response
    monkeypatch.setattr(api_client, "Session", lambda: session)

    with pytest.raises(APIError, match="ne contient pas de jeton"):
        api_client.authenticate_internal(
            "https://server.example",
            8443,
            "admin",
            "password",
        )

    session.post.assert_not_called()
