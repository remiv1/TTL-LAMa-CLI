"""Tests for administrative device commands."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands.admin import devices as devices_commands
from ttlama_cli.exc import APIError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


DEVICE_ID = 42
DEVICE_RESPONSE = {
    "id": DEVICE_ID,
    "user_id": "user-123",
    "name": "work-laptop",
    "public_key": "device-public-key",
    "created_at": "2026-10-30T19:30:58+00:00",
    "revoked_at": None,
}
DEVICE_UPDATE_DATA = {
    "name": "work-laptop",
    "public_key": "device-public-key",
}


def _mock_device_command_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    request_api: Mock,
) -> None:
    monkeypatch.setattr(
        devices_commands,
        "_get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(devices_commands, "request_api", request_api)


def _get_request(mock: Mock, index: int = -1) -> SpecificRequest:
    return mock.call_args_list[index].kwargs["specific_request"]


def test_admin_devices_group_is_registered() -> None:
    """The admin device group exposes all documented commands."""
    result = CliRunner().invoke(app, ["admin", "devices", "--help"])

    assert result.exit_code == 0
    for command in ("list", "get", "update", "block", "delete"):
        assert command in result.output


def test_list_devices_sends_combined_filters_and_yaml_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """List combines lease and profile filters and wraps YAML rows by resource."""
    request_api = Mock(return_value=[DEVICE_RESPONSE])
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        [
            "admin", "devices", "list", "--lease", "9", "--profile", "17", "--yaml",
        ],
    )

    assert result.exit_code == 0
    assert yaml.safe_load(result.output) == {"devices": [DEVICE_RESPONSE]}
    request = _get_request(request_api)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == "admin/devices"
    assert request.params == {"lease": 9, "profile": 17}


def test_list_devices_table_omits_public_key_and_shows_block_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default list is compact and identifies revoked devices."""
    blocked_device = {**DEVICE_RESPONSE, "revoked_at": "2026-10-31T10:00:00+00:00"}
    request_api = Mock(return_value=[DEVICE_RESPONSE, blocked_device])
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["admin", "devices", "list"])

    assert result.exit_code == 0
    assert "work-laptop" in result.output
    assert "active" in result.output
    assert "blocked" in result.output
    assert "device-public-key" not in result.output


def test_list_devices_reports_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty device list is reported as an unsuccessful lookup."""
    request_api = Mock(return_value=[])
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["admin", "devices", "list"])

    assert result.exit_code == 1
    assert "No devices found." in result.output


@pytest.mark.parametrize("output_flag", ["--json", "--yaml"])
def test_get_device_structured_output_can_be_used_as_update_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_flag: str,
) -> None:
    """Get emits only flat editable fields in structured output."""
    request_api = Mock(side_effect=[DEVICE_RESPONSE, {}])
    _mock_device_command_dependencies(monkeypatch, request_api)
    runner = CliRunner()

    get_result = runner.invoke(
        app,
        ["admin", "devices", "get", "--device", str(DEVICE_ID), output_flag],
    )
    assert get_result.exit_code == 0
    if output_flag == "--json":
        update_data = json.loads(get_result.output)
    else:
        update_data = yaml.safe_load(get_result.output)
    assert update_data == DEVICE_UPDATE_DATA

    file_path = tmp_path / "device.yaml"
    file_path.write_text(get_result.output, encoding="utf-8")
    update_result = runner.invoke(
        app,
        [
            "admin", "devices", "update", "--device", str(DEVICE_ID),
            "--file", str(file_path),
        ],
    )

    assert update_result.exit_code == 0
    get_request = _get_request(request_api, 0)
    assert get_request.method is HTTPMethod.GET
    assert get_request.endpoint == f"admin/devices/{DEVICE_ID}"
    update_request = _get_request(request_api, 1)
    assert update_request.method is HTTPMethod.PATCH
    assert update_request.endpoint == f"admin/devices/{DEVICE_ID}"
    assert update_request.json_body == DEVICE_UPDATE_DATA


def test_get_device_console_displays_complete_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The console detail view includes ownership, lifecycle, and key data."""
    request_api = Mock(return_value=DEVICE_RESPONSE)
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "devices", "get", "--device", str(DEVICE_ID)],
    )

    assert result.exit_code == 0
    for value in (str(DEVICE_ID), "user-123", "work-laptop", "device-public-key"):
        assert value in result.output
    request = _get_request(request_api)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == f"admin/devices/{DEVICE_ID}"


@pytest.mark.parametrize(
    ("suffix", "contents"),
    [
        (".yaml", "name: updated-laptop\n"),
        (".json", '{"public_key": "updated-public-key"}'),
    ],
)
def test_update_device_parses_json_and_yaml_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
    contents: str,
) -> None:
    """Update sends parsed JSON and YAML fields as a PATCH request."""
    file_path = tmp_path / f"device{suffix}"
    file_path.write_text(contents, encoding="utf-8")
    request_api = Mock(return_value=DEVICE_RESPONSE)
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        [
            "admin", "devices", "update", "--device", str(DEVICE_ID),
            "--file", str(file_path),
        ],
    )

    assert result.exit_code == 0
    request = _get_request(request_api)
    assert request.method is HTTPMethod.PATCH
    assert request.endpoint == f"admin/devices/{DEVICE_ID}"
    expected_data = yaml.safe_load(contents) if suffix == ".yaml" else json.loads(contents)
    assert request.json_body == expected_data


@pytest.mark.parametrize(
    ("command", "method", "endpoint", "success_message"),
    [
        ("block", HTTPMethod.POST, f"admin/devices/{DEVICE_ID}/block", "active leases were revoked"),
        ("delete", HTTPMethod.DELETE, f"admin/devices/{DEVICE_ID}", "history retained"),
    ],
)
def test_block_and_delete_confirm_before_mutating(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    method: HTTPMethod,
    endpoint: str,
    success_message: str,
) -> None:
    """Both destructive commands confirm and call their documented endpoint."""
    request_api = Mock(return_value=DEVICE_RESPONSE)
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "devices", command, "--device", str(DEVICE_ID)],
        input="y\n",
    )

    assert result.exit_code == 0
    assert success_message in result.output
    request = _get_request(request_api)
    assert request.method is method
    assert request.endpoint == endpoint
    assert request.json_body is None


@pytest.mark.parametrize("command", ["block", "delete"])
def test_block_and_delete_cancellation_makes_no_api_request(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    """Declining confirmation prevents both API access and mutation."""
    request_api = Mock()
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "devices", command, "--device", str(DEVICE_ID)],
        input="n\n",
    )

    assert result.exit_code == 1
    assert "not" in result.output
    request_api.assert_not_called()


def test_update_rejects_non_object_file_before_api_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Device update files must contain an object at the top level."""
    file_path = tmp_path / "device.yaml"
    file_path.write_text("- work-laptop\n", encoding="utf-8")
    request_api = Mock()
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        [
            "admin", "devices", "update", "--device", str(DEVICE_ID),
            "--file", str(file_path),
        ],
    )

    assert result.exit_code == 1
    assert "object at the top level" in result.output
    request_api.assert_not_called()


def test_list_devices_rejects_invalid_api_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed API list response exits without a traceback."""
    request_api = Mock(return_value={"devices": [DEVICE_RESPONSE]})
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["admin", "devices", "list"])

    assert result.exit_code == 1
    assert "isn't a device list" in result.output
    assert "Traceback" not in result.output


def test_list_devices_reports_api_errors_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API failures are rendered as CLI errors without a traceback."""
    request_api = Mock(side_effect=APIError("Device listing failed."))
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(app, ["admin", "devices", "list"])

    assert result.exit_code == 1
    assert "Device listing failed." in result.output
    assert "Traceback" not in result.output
    request_api.assert_called_once()


def test_list_devices_rejects_multiple_structured_formats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON and YAML output cannot be selected at the same time."""
    request_api = Mock()
    _mock_device_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "devices", "list", "--json", "--yaml"],
    )

    assert result.exit_code == 1
    assert "Choose only one" in result.output
    request_api.assert_not_called()
