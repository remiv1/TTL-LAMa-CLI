"""Tests for authenticated device and lease commands."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.exc import APIError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


DEVICE = {
    "id": 4,
    "user_id": "user-123",
    "name": "laptop",
    "public_key": "public-key",
    "created_at": "2026-10-30T12:00:00+00:00",
    "revoked_at": None,
}
LEASE = {
    "id": 9,
    "user_id": "user-123",
    "device_id": 4,
    "profile_user_id": 6,
    "profile_id": 17,
    "created_at": "2026-10-30T12:00:00+00:00",
    "ended_at": "2026-10-30T13:00:00+00:00",
    "revoked_at": None,
    "status": "active",
}


def _mock_user_api(
    monkeypatch: pytest.MonkeyPatch,
    request_api: Mock,
) -> None:
    monkeypatch.setattr(
        "ttlama_cli.commands.get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr("ttlama_cli.commands.request_api", request_api)


def _request_at(mock: Mock, index: int = -1) -> SpecificRequest:
    return mock.call_args_list[index].kwargs["specific_request"]


def test_device_list_and_get_support_json_and_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """List and get use the self-service API and structured output helpers."""
    request_api = Mock(side_effect=[[DEVICE], DEVICE])
    _mock_user_api(monkeypatch, request_api)
    runner = CliRunner()

    list_result = runner.invoke(app, ["user", "devices", "list", "--json"])
    get_result = runner.invoke(
        app,
        ["user", "devices", "get", "--id", "4", "--yaml"],
    )

    assert list_result.exit_code == 0
    assert json.loads(list_result.output) == [DEVICE]
    assert get_result.exit_code == 0
    assert yaml.safe_load(get_result.output) == DEVICE
    assert _request_at(request_api, 0).method is HTTPMethod.GET
    assert _request_at(request_api, 0).endpoint == "users/me/devices"
    assert _request_at(request_api, 1).endpoint == "users/me/devices/4"


@pytest.mark.parametrize(
    "command",
    [
        ["user", "devices", "get", "--id", "4"],
        ["user", "leases", "get", "--id", "9"],
    ],
)
def test_get_commands_report_api_errors_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
) -> None:
    """Get commands report server errors cleanly and do not print tracebacks."""
    request_api = Mock(side_effect=APIError("Resource not found."))
    _mock_user_api(monkeypatch, request_api)

    result = CliRunner().invoke(app, command)

    assert result.exit_code == 1
    assert "Resource not found." in result.output
    assert "Traceback" not in result.output
    request_api.assert_called_once()


@pytest.mark.parametrize(
    "command",
    [
        ["user", "devices", "list", "--json", "--yaml"],
        ["user", "leases", "list", "--json", "--yaml"],
    ],
)
def test_list_rejects_multiple_output_formats(
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
) -> None:
    """List commands accept at most one structured output format."""
    request_api = Mock()
    _mock_user_api(monkeypatch, request_api)

    result = CliRunner().invoke(app, command)

    assert result.exit_code == 1
    assert "Choose only one output option" in result.output
    request_api.assert_not_called()


@pytest.mark.parametrize(
    ("resource", "output_option", "expected"),
    [
        ("devices", "--json", []),
        ("devices", "--yaml", {"devices": []}),
        ("leases", "--json", []),
        ("leases", "--yaml", {"leases": []}),
    ],
)
def test_empty_lists_preserve_selected_output_format(
    monkeypatch: pytest.MonkeyPatch,
    resource: str,
    output_option: str,
    expected: object,
) -> None:
    """Empty list responses still produce valid structured output."""
    request_api = Mock(return_value=[])
    _mock_user_api(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["user", resource, "list", output_option],
    )

    assert result.exit_code == 0
    parsed = (
        json.loads(result.output)
        if output_option == "--json"
        else yaml.safe_load(result.output)
    )
    assert parsed == expected


def test_device_add_loads_yaml_and_posts_the_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Add accepts a YAML object and sends only its supplied fields."""
    file_path = tmp_path / "device.yaml"
    file_path.write_text("name: laptop\npublic_key: public-key\n", encoding="utf-8")
    request_api = Mock(return_value=DEVICE)
    _mock_user_api(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["user", "devices", "add", "--file", str(file_path)],
    )

    assert result.exit_code == 0
    assert "Device 4 added successfully." in result.output
    request = _request_at(request_api)
    assert request.method is HTTPMethod.POST
    assert request.endpoint == "users/me/devices"
    assert request.json_body == {"name": "laptop", "public_key": "public-key"}


def test_device_delete_confirms_and_sends_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delete asks for confirmation before revoking the device."""
    request_api = Mock(return_value=None)
    _mock_user_api(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["user", "devices", "delete", "--id", "4"],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Device 4 revoked successfully." in result.output
    request = _request_at(request_api)
    assert request.method is HTTPMethod.DELETE
    assert request.endpoint == "users/me/devices/4"


def test_lease_list_and_get_support_json_and_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """List and get use the self-service API and structured output helpers."""
    request_api = Mock(side_effect=[[LEASE], LEASE])
    _mock_user_api(monkeypatch, request_api)
    runner = CliRunner()

    list_result = runner.invoke(app, ["user", "leases", "list", "--yaml"])
    get_result = runner.invoke(
        app,
        ["user", "leases", "get", "--id", "9", "--json"],
    )

    assert list_result.exit_code == 0
    assert yaml.safe_load(list_result.output) == {"leases": [LEASE]}
    assert get_result.exit_code == 0
    assert json.loads(get_result.output) == LEASE
    assert _request_at(request_api, 0).endpoint == "users/me/leases"
    assert _request_at(request_api, 1).endpoint == "users/me/leases/9"


def test_lease_create_loads_json_and_posts_the_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create reads the JSON lease body and sends it unchanged."""
    lease_data = {"device_id": 4, "profile_id": 17}
    file_path = tmp_path / "lease.json"
    file_path.write_text(json.dumps(lease_data), encoding="utf-8")
    request_api = Mock(return_value=LEASE)
    _mock_user_api(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["user", "leases", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 0
    assert "Lease 9 created successfully." in result.output
    request = _request_at(request_api)
    assert request.method is HTTPMethod.POST
    assert request.endpoint == "users/me/leases"
    assert request.json_body == lease_data


def test_lease_revoke_confirms_and_sends_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Revoke asks for confirmation before changing lease state."""
    request_api = Mock(return_value=LEASE)
    _mock_user_api(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["user", "leases", "revoke", "--id", "9"],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Lease 9 revoked successfully." in result.output
    request = _request_at(request_api)
    assert request.method is HTTPMethod.POST
    assert request.endpoint == "users/me/leases/9/revoke"
