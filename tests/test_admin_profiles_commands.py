"""Tests for administrative profile commands."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands.admin import profiles as profiles_commands
from ttlama_cli.exc import APIError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


PROFILE_ID = 17
PROFILE_RESPONSE = {
    "id": PROFILE_ID,
    "name": "office-access",
    "created_at": "2026-10-30T19:30:58+00:00",
    "revoked_at": None,
    "policy": {
        "default_duration": "1h",
        "maximum_duration": "8h",
        "networks": ["10.0.0.0/24", "192.168.10.0/24"],
    },
}
PROFILE_UPDATE_DATA = {
    "name": "office-access",
    "default_duration": "1h",
    "maximum_duration": "8h",
    "networks": ["10.0.0.0/24", "192.168.10.0/24"],
}


def _mock_profile_command_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    request_api: Mock,
) -> None:
    monkeypatch.setattr(
        profiles_commands,
        "_get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(profiles_commands, "request_api", request_api)


def _get_request(mock: Mock, index: int = -1) -> SpecificRequest:
    return mock.call_args_list[index].kwargs["specific_request"]


def test_list_profiles_sends_combined_filters_and_yaml_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """List combines all supplied filters and wraps YAML rows by resource."""
    request_api = Mock(return_value=[PROFILE_RESPONSE])
    _mock_profile_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        [
            "admin",
            "profiles",
            "list",
            "--user",
            "user-123",
            "--device",
            "4",
            "--lease",
            "9",
            "--yaml",
        ],
    )

    assert result.exit_code == 0
    assert yaml.safe_load(result.output) == {"profiles": [PROFILE_RESPONSE]}
    request = _get_request(request_api)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == "admin/profiles"
    assert request.params == {"user": "user-123", "device": 4, "lease": 9}


@pytest.mark.parametrize("output_flag", ["--json", "--yaml"])
def test_get_profile_output_can_be_used_as_update_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_flag: str,
) -> None:
    """Get emits only flat profile fields accepted by the update API."""
    request_api = Mock(side_effect=[PROFILE_RESPONSE, {}])
    _mock_profile_command_dependencies(monkeypatch, request_api)
    runner = CliRunner()

    get_result = runner.invoke(
        app,
        ["admin", "profiles", "get", "--profile", str(PROFILE_ID), output_flag],
    )
    assert get_result.exit_code == 0
    if output_flag == "--json":
        update_data = json.loads(get_result.output)
    else:
        update_data = yaml.safe_load(get_result.output)
    assert update_data == PROFILE_UPDATE_DATA

    file_path = tmp_path / "profile.yaml"
    file_path.write_text(get_result.output, encoding="utf-8")
    update_result = runner.invoke(
        app,
        [
            "admin",
            "profiles",
            "update",
            "--profile",
            str(PROFILE_ID),
            "--file",
            str(file_path),
        ],
    )

    assert update_result.exit_code == 0
    get_request = _get_request(request_api, 0)
    assert get_request.method is HTTPMethod.GET
    assert get_request.endpoint == f"admin/profiles/{PROFILE_ID}"
    update_request = _get_request(request_api, 1)
    assert update_request.method is HTTPMethod.PATCH
    assert update_request.endpoint == f"admin/profiles/{PROFILE_ID}"
    assert update_request.json_body == PROFILE_UPDATE_DATA


def test_get_legacy_profile_without_policy_returns_name_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A historical profile without a policy still has usable get output."""
    request_api = Mock(return_value={"id": PROFILE_ID, "name": "legacy", "policy": None})
    _mock_profile_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "profiles", "get", "--profile", str(PROFILE_ID), "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {"name": "legacy"}


def test_create_profile_sends_yaml_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create parses a YAML profile body and sends it to the API."""
    file_path = tmp_path / "profile.yaml"
    file_path.write_text(
        "name: office-access\n"
        "default_duration: 1h\n"
        "maximum_duration: 8h\n"
        "networks:\n"
        "  - 10.0.0.0/24\n",
        encoding="utf-8",
    )
    request_api = Mock(return_value=PROFILE_RESPONSE)
    _mock_profile_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "profiles", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 0
    assert "Profile created successfully." in result.output
    request = _get_request(request_api)
    assert request.method is HTTPMethod.POST
    assert request.endpoint == "admin/profiles"
    assert request.json_body == {
        "name": "office-access",
        "default_duration": "1h",
        "maximum_duration": "8h",
        "networks": ["10.0.0.0/24"],
    }


def test_delete_profile_sends_revoke_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delete uses the API's profile revocation endpoint."""
    request_api = Mock(return_value=None)
    _mock_profile_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "profiles", "delete", "--profile", str(PROFILE_ID)],
    )

    assert result.exit_code == 0
    assert "revoked successfully" in result.output
    request = _get_request(request_api)
    assert request.method is HTTPMethod.DELETE
    assert request.endpoint == f"admin/profiles/{PROFILE_ID}"


def test_create_profile_rejects_non_object_file_before_api_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profile input must be an object before making an API request."""
    file_path = tmp_path / "profile.yaml"
    file_path.write_text("- office-access\n", encoding="utf-8")
    request_api = Mock()
    _mock_profile_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "profiles", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 1
    assert "object at the top level" in result.output
    request_api.assert_not_called()


def test_create_profile_reports_api_errors_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API errors are shown without a traceback."""
    file_path = tmp_path / "profile.json"
    file_path.write_text(json.dumps(PROFILE_UPDATE_DATA), encoding="utf-8")
    request_api = Mock(side_effect=APIError("Profile name already exists."))
    _mock_profile_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "profiles", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 1
    assert "Profile name already exists." in result.output
    assert "Traceback" not in result.output
