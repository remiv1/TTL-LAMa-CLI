"""Tests for administrative user commands."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands.admin import users as users_commands
from ttlama_cli.exc import APIError
from ttlama_cli.objects import HTTPMethod, SpecificRequest


USER_ID = "user-123"


def _mock_user_command_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    request_api: Mock,
) -> None:
    monkeypatch.setattr(
        users_commands,
        "_get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(users_commands, "request_api", request_api)


def _get_request(mock: Mock) -> SpecificRequest:
    return mock.call_args.kwargs["specific_request"]


def test_create_user_sends_yaml_file_to_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create sends parsed user data as a POST request."""
    file_path = tmp_path / "user.yaml"
    file_path.write_text("username: alice\nis_admin: true\n", encoding="utf-8")
    request_api = Mock(return_value={})
    _mock_user_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "users", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 0
    assert "User created successfully." in result.output
    request = _get_request(request_api)
    assert request.method is HTTPMethod.POST
    assert request.endpoint == "admin/users"
    assert request.json_body == {"username": "alice", "is_admin": True}


def test_create_user_displays_generated_password_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generated password is shown only when the API returns it on creation."""
    file_path = tmp_path / "user.yaml"
    file_path.write_text("username: alice\n", encoding="utf-8")
    generated_password = "one-time-generated-password"
    request_api = Mock(return_value={
        "user": {"username": "alice"},
        "generated_password": generated_password,
    })
    _mock_user_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "users", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 0
    assert generated_password in result.output
    assert "shown only once" in result.output


def test_update_user_sends_json_file_to_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Update sends parsed user fields as a PATCH request."""
    file_path = tmp_path / "user.json"
    file_path.write_text('{"email": null, "enabled": false}', encoding="utf-8")
    request_api = Mock(return_value={})
    _mock_user_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        [
            "admin",
            "users",
            "update",
            "--user",
            "user-123",
            "--file",
            str(file_path),
        ],
    )

    assert result.exit_code == 0
    assert "User user-123 updated successfully." in result.output
    request = _get_request(request_api)
    assert request.method is HTTPMethod.PATCH
    assert request.endpoint == "admin/users/user-123"
    assert request.json_body == {"email": None, "enabled": False}


def test_delete_user_sends_delete_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delete targets the requested user ID."""
    request_api = Mock(return_value=None)
    _mock_user_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "users", "delete", "--user", "user-123"],
    )

    assert result.exit_code == 0
    assert "User user-123 deleted successfully." in result.output
    request = _get_request(request_api)
    assert request.method is HTTPMethod.DELETE
    assert request.endpoint == "admin/users/user-123"
    assert request.json_body is None


def test_create_user_reports_invalid_input_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid top-level data is rejected before contacting the API."""
    file_path = tmp_path / "user.yaml"
    file_path.write_text("- alice\n", encoding="utf-8")
    request_api = Mock()
    _mock_user_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "users", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 1
    assert "must contain an object" in result.output
    request_api.assert_not_called()


def test_create_user_reports_api_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API failures are reported without a traceback."""
    file_path = tmp_path / "user.json"
    file_path.write_text('{"username": "alice"}', encoding="utf-8")
    request_api = Mock(side_effect=APIError("Server rejected the user."))
    _mock_user_command_dependencies(monkeypatch, request_api)

    result = CliRunner().invoke(
        app,
        ["admin", "users", "create", "--file", str(file_path)],
    )

    assert result.exit_code == 1
    assert "Server rejected the user." in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    ("output_format", "file_suffix"),
    [("--json", ".json"), ("--yaml", ".yaml")],
)
def test_get_user_output_can_be_used_as_update_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_format: str,
    file_suffix: str,
) -> None:
    """Get output is a flat update body in both supported formats."""
    user_response = {
        "id": USER_ID,
        "username": "alice",
        "email": "alice@example.test",
        "enabled": True,
        "is_admin": False,
        "created_at": "2026-10-30T19:30:58+00:00",
        "last_login": None,
    }
    request_api = Mock(side_effect=[user_response, {}])
    _mock_user_command_dependencies(monkeypatch, request_api)
    runner = CliRunner()

    get_result = runner.invoke(
        app,
        ["admin", "users", "get", USER_ID, output_format],
    )
    assert get_result.exit_code == 0
    assert "id:" not in get_result.output
    assert "created_at:" not in get_result.output
    assert "last_login:" not in get_result.output

    file_path = tmp_path / f"user{file_suffix}"
    file_path.write_text(get_result.output, encoding="utf-8")
    update_result = runner.invoke(
        app,
        [
            "admin",
            "users",
            "update",
            "--user",
            USER_ID,
            "--file",
            str(file_path),
        ],
    )

    assert update_result.exit_code == 0
    update_request = request_api.call_args_list[1].kwargs["specific_request"]
    assert update_request.method is HTTPMethod.PATCH
    assert update_request.endpoint == f"admin/users/{USER_ID}"
    assert update_request.json_body == {
        "username": "alice",
        "email": "alice@example.test",
        "enabled": True,
        "is_admin": False,
    }
