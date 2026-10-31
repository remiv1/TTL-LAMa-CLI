"""Tests for authenticated user commands."""

import json
from unittest.mock import Mock

import pytest
import yaml
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.exc import APIError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


PROFILE = {
    "id": 17,
    "name": "office-access",
    "policy": {
        "default_duration": "1h",
        "maximum_duration": "8h",
        "networks": ["10.0.0.0/24"],
    },
}
OVERVIEW = {
    "user": {
        "id": "user-123",
        "username": "alice",
        "email": "alice@example.test",
        "is_admin": False,
    },
    "devices": [
        {
            "id": 4,
            "name": "laptop",
            "created_at": "2026-10-30T12:00:00+00:00",
            "revoked_at": None,
        }
    ],
    "leases": [
        {
            "id": 9,
            "device_id": 4,
            "profile_id": 17,
            "ended_at": "2026-10-30T13:00:00+00:00",
            "status": "active",
        }
    ],
    "profiles": [PROFILE],
}


def _mock_user_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    request_api: Mock,
) -> None:
    monkeypatch.setattr(
        "ttlama_cli.commands.user.get.get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(
        "ttlama_cli.commands.user.profiles.get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr("ttlama_cli.commands.request_api", request_api)


def _get_request(mock: Mock) -> SpecificRequest:
    return mock.call_args.kwargs["specific_request"]


def test_user_get_returns_the_full_overview_as_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Get fetches the self-service overview and preserves its resources."""
    request_api = Mock(return_value=OVERVIEW)
    _mock_user_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["user", "get", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == OVERVIEW
    request = _get_request(request_api)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == "users/me/overview"


def test_user_profiles_list_displays_assigned_profiles_as_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profiles list uses the shared overview endpoint and wraps YAML output."""
    request_api = Mock(return_value=OVERVIEW)
    _mock_user_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["user", "profiles", "list", "--yaml"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.output) == {"profiles": [PROFILE]}
    request = _get_request(request_api)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == "users/me/overview"


def test_user_profiles_get_returns_one_assigned_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profiles get selects a profile from the authenticated user's assignments."""
    request_api = Mock(return_value=OVERVIEW)
    _mock_user_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["user", "profiles", "get", "--id", "17", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == PROFILE


def test_user_profiles_list_accepts_no_assignments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty assignment list is a successful result for a regular user."""
    overview = {**OVERVIEW, "profiles": []}
    request_api = Mock(return_value=overview)
    _mock_user_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["user", "profiles", "list"])

    assert result.exit_code == 0
    assert "No profiles assigned." in result.output


def test_user_profile_get_rejects_an_unassigned_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A profile outside the authenticated user's assignments is not returned."""
    request_api = Mock(return_value=OVERVIEW)
    _mock_user_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["user", "profiles", "get", "--id", "18"],
    )

    assert result.exit_code == 1
    assert "not assigned to this user" in result.output


def test_user_command_reports_api_errors_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API failures are rendered without an internal traceback."""
    request_api = Mock(side_effect=APIError("The API is unavailable."))
    _mock_user_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["user", "get"])

    assert result.exit_code == 1
    assert "The API is unavailable." in result.output
    assert "Traceback" not in result.output
