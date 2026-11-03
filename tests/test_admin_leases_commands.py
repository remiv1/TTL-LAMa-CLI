"""Tests for administrative lease commands."""

import json
from unittest.mock import Mock

import pytest
import yaml
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands.admin import leases as leases_commands
from ttlama_cli.exc import APIError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


LEASE_ID = 73
LEASE_RESPONSE = {
    "id": LEASE_ID,
    "user_id": "user-123",
    "device_id": 42,
    "profile_user_id": 17,
    "profile_id": 9,
    "created_at": "2026-11-02T09:00:00+00:00",
    "ended_at": "2026-11-02T10:00:00+00:00",
    "revoked_at": None,
    "status": "active",
}


def _mock_lease_command_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    request_api: Mock,
) -> None:
    monkeypatch.setattr(
        leases_commands,
        "_get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(leases_commands, "request_api", request_api)


def _get_request(mock: Mock, index: int = -1) -> SpecificRequest:
    return mock.call_args_list[index].kwargs["specific_request"]


def test_admin_leases_group_is_registered() -> None:
    """The admin lease group exposes its list, get, and revoke commands."""
    runner = CliRunner()
    result = runner.invoke(app, ["admin", "leases", "--help"])

    assert result.exit_code == 0
    for command in ("list", "get", "revoke"):
        assert command in result.output

        command_help = runner.invoke(
            app,
            ["admin", "leases", command, "--help"],
        )
        assert command_help.exit_code == 0
        assert ":param " not in command_help.output
    assert "active|expired|revoked" in runner.invoke(
        app,
        ["admin", "leases", "list", "--help"],
    ).output


def test_list_leases_sends_all_filters_and_yaml_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """List combines all supported lease filters and wraps YAML rows."""
    request_api = Mock(return_value=[LEASE_RESPONSE])
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        [
            "admin", "leases", "list", "--user", "user-123", "--device", "42",
            "--profile", "9", "--status", "active", "--yaml",
        ],
    )

    assert result.exit_code == 0
    assert yaml.safe_load(result.output) == {"leases": [LEASE_RESPONSE]}
    request = _get_request(request_api)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == "admin/leases"
    assert request.params == {
        "user": "user-123",
        "device": 42,
        "profile": 9,
        "status": "active",
    }


def test_list_leases_table_shows_status_and_omits_internal_assignment_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Rich table shows useful lease fields without assignment internals."""
    request_api = Mock(return_value=[LEASE_RESPONSE])
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["admin", "leases", "list"])

    assert result.exit_code == 0
    for value in (str(LEASE_ID), "user-123", "42", "9", "active"):
        assert value in result.output
    assert "profile_user_id" not in result.output


def test_list_leases_reports_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty lease list exits with a clear message."""
    request_api = Mock(return_value=[])
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["admin", "leases", "list"])

    assert result.exit_code == 1
    assert "No leases found." in result.output


def test_list_leases_rejects_invalid_api_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed API list response exits without a traceback."""
    request_api = Mock(return_value={"leases": [LEASE_RESPONSE]})
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["admin", "leases", "list"])

    assert result.exit_code == 1
    assert "isn't a lease list" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize("output_flag", ["--json", "--yaml"])
def test_get_lease_structured_output_preserves_all_fields(
    monkeypatch: pytest.MonkeyPatch,
    output_flag: str,
) -> None:
    """Structured get output preserves the complete lease response."""
    request_api = Mock(return_value=LEASE_RESPONSE)
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "leases", "get", "--lease", str(LEASE_ID), output_flag],
    )

    assert result.exit_code == 0
    actual = json.loads(result.output) if output_flag == "--json" else yaml.safe_load(result.output)
    assert actual == LEASE_RESPONSE
    request = _get_request(request_api)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == f"admin/leases/{LEASE_ID}"


def test_get_lease_console_displays_complete_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The console detail view includes lifecycle and relationship fields."""
    request_api = Mock(return_value=LEASE_RESPONSE)
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "leases", "get", "--lease", str(LEASE_ID)],
    )

    assert result.exit_code == 0
    for value in (str(LEASE_ID), "user-123", "profile_user_id", "revoked_at", "active"):
        assert value in result.output


def test_revoke_lease_confirms_before_post(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Revoke confirms, then calls the documented endpoint and retains history."""
    request_api = Mock(return_value=LEASE_RESPONSE)
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "leases", "revoke", "--lease", str(LEASE_ID)],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "history retained" in result.output
    request = _get_request(request_api)
    assert request.method is HTTPMethod.POST
    assert request.endpoint == f"admin/leases/{LEASE_ID}/revoke"
    assert request.json_body is None


def test_revoke_lease_cancellation_makes_no_api_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Declining confirmation prevents the API request."""
    request_api = Mock()
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "leases", "revoke", "--lease", str(LEASE_ID)],
        input="n\n",
    )

    assert result.exit_code == 1
    assert "Lease was not revoked." in result.output
    request_api.assert_not_called()


def test_revoke_lease_reports_api_errors_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API failures are rendered as CLI errors without a traceback."""
    request_api = Mock(side_effect=APIError("Lease revocation failed."))
    _mock_lease_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "leases", "revoke", "--lease", str(LEASE_ID)],
        input="y\n",
    )

    assert result.exit_code == 1
    assert "Lease revocation failed." in result.output
    assert "Traceback" not in result.output
