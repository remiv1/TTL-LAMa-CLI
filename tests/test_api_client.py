"""Tests du client HTTP d’authentification."""

from unittest.mock import Mock

import pytest
from requests.exceptions import ConnectionError, HTTPError  # pylint: disable=W0622

from ttlama_cli import api_client
from ttlama_cli.exc import APIError, AuthenticationError, AuthorizationError
from ttlama_cli.objects import ServerParameters, SpecificRequest, HTTPMethod


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

def test_request_api_sends_bearer_and_returns_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teste que la fonction envoie le token Bearer et renvoie le JSON."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = [
        {
            "id": 1,
            "username": "alice"
        },
    ]
    mocked_request = Mock(return_value=response)
    monkeypatch.setattr(api_client, "request", mocked_request)

    result = api_client.request_api(
        ServerParameters(
            server_url="https://server.example",
            server_port=8443,
        ),
        "test-token",
        SpecificRequest(
            endpoint="admin/users",
            method=HTTPMethod.GET,
            params={"device": 12},
        ),
    )

    assert result == [
        {
            "id": 1,
            "username": "alice",
        },
    ]
    mocked_request.assert_called_once_with(
        "GET",
        "https://server.example:8443/api/v1/admin/users",
        headers={"Authorization": "Bearer test-token"},
        params={"device": 12},
        json=None,
        timeout=5,
    )

@pytest.mark.parametrize(
    "status_code, expected_exception, match",
    [
        (401, AuthenticationError, "Bearer token is invalid."),
        (403, AuthorizationError, "You haven't admin privileges."),
        (500, APIError, "TTL-LAMa API responded with HTTP status 500."),
    ],
)
def test_request_api_raises_for_status_codes(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_exception: type[Exception],
    match: str,
) -> None:
    """Teste que la fonction lève les exceptions appropriées pour les codes de statut HTTP."""
    response = Mock()
    response.status_code = status_code
    response.raise_for_status.side_effect = HTTPError("error")
    mocked_request = Mock(return_value=response)
    monkeypatch.setattr(api_client, "request", mocked_request)

    with pytest.raises(expected_exception, match=match):
        api_client.request_api(
            ServerParameters(server_url="https://server.example", server_port=8443),
            "test-token",
            SpecificRequest(endpoint="admin/users", method=HTTPMethod.GET),
        )
