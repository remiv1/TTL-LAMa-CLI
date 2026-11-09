"""Exercise CLI workflows against the Compose server."""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from ttlama_cli import token_store
from ttlama_cli.cli import app

_REQUIRED_ENVIRONMENT = (
    "TTLAMA_TEST_SERVER_URL",
    "TTLAMA_TEST_SERVER_PORT",
    "TTLAMA_TEST_ADMIN_USERNAME",
    "TTLAMA_TEST_ADMIN_PASSWORD",
)
pytestmark = pytest.mark.skipif(
    not all(os.environ.get(name) for name in _REQUIRED_ENVIRONMENT),
    reason="Integration tests require their Compose environment.",
)


@pytest.fixture(name="memory_keyring")
def isolated_memory_keyring(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[tuple[str, str], str]:
    """Use isolated in-memory token storage for each CLI workflow."""
    tokens: dict[tuple[str, str], str] = {}

    def set_password(service: str, account: str, password: str) -> None:
        tokens[(service, account)] = password

    def get_password(service: str, account: str) -> str | None:
        return tokens.get((service, account))

    def delete_password(service: str, account: str) -> None:
        tokens.pop((service, account), None)

    monkeypatch.setattr(token_store.keyring, "set_password", set_password)
    monkeypatch.setattr(token_store.keyring, "get_password", get_password)
    monkeypatch.setattr(token_store.keyring, "delete_password", delete_password)
    return tokens


@pytest.fixture(name="server_config")
def configured_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[str, int, str, str]:
    """Configure the CLI for the Compose server and an isolated XDG directory."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return (
        os.environ["TTLAMA_TEST_SERVER_URL"],
        int(os.environ["TTLAMA_TEST_SERVER_PORT"]),
        os.environ["TTLAMA_TEST_ADMIN_USERNAME"],
        os.environ["TTLAMA_TEST_ADMIN_PASSWORD"],
    )


def _invoke(
    runner: CliRunner,
    command: list[str],
    *,
    input_text: str | None = None,
    exit_code: int = 0,
) -> Any:
    result = runner.invoke(app, command, input=input_text)
    assert result.exit_code == exit_code, result.output
    assert "Traceback" not in result.output
    return result


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _json_value(result: Any) -> Any:
    return json.loads(result.output)


def _json_rows(result: Any, root: str | None = None) -> list[dict[str, object]]:
    payload: object = _json_value(result)
    if isinstance(payload, dict) and root is not None:
        payload = cast(dict[str, object], payload)[root]
    assert isinstance(payload, list), result.output
    rows = cast(list[object], payload)
    assert all(isinstance(row, dict) for row in rows), result.output
    return cast(list[dict[str, object]], payload)


def _find_row(
    rows: list[dict[str, object]],
    field: str,
    value: object,
) -> dict[str, object]:
    row = next((item for item in rows if item.get(field) == value), None)
    assert row is not None, rows
    return row


def _int_field(row: dict[str, object], field: str) -> int:
    value = row.get(field)
    assert isinstance(value, int), row
    return value


def _configure_server(runner: CliRunner, server_config: tuple[str, int, str, str]) -> None:
    server_url, server_port, _, _ = server_config
    result = _invoke(
        runner,
        ["config", "set-server", server_url, "--port", str(server_port)],
    )
    assert "Server configuration saved." in result.output


def _login(runner: CliRunner, username: str, password: str) -> Any:
    return _invoke(
        runner,
        ["auth", "login", "internal", "--user", username],
        input_text=f"{password}\n",
    )


def _admin_login(
    runner: CliRunner,
    server_config: tuple[str, int, str, str],
) -> Any:
    _, _, username, password = server_config
    result = _login(runner, username, password)
    assert "Login successful" in result.output
    return result


def _create_user(
    runner: CliRunner,
    tmp_path: Path,
    username: str,
    password: str,
) -> dict[str, object]:
    user_file = tmp_path / f"{username}.json"
    _write_json(
        user_file,
        {
            "username": username,
            "email": f"{username}@example.test",
            "password": password,
        },
    )
    result = _invoke(
        runner,
        ["admin", "users", "create", "--file", str(user_file)],
    )
    assert "User created successfully." in result.output
    assert password not in result.output
    return _find_row(
        _json_rows(_invoke(runner, ["admin", "users", "ls", "--json"])),
        "username",
        username,
    )


def _create_profile(
    runner: CliRunner,
    tmp_path: Path,
    profile_name: str,
) -> dict[str, object]:
    profile_file = tmp_path / f"{profile_name}.json"
    _write_json(
        profile_file,
        {
            "name": profile_name,
            "default_duration": "1h",
            "maximum_duration": "4h",
            "lease_target": "wg0",
            "networks": ["10.0.0.0/24"],
        },
    )
    result = _invoke(
        runner,
        ["admin", "profiles", "create", "--file", str(profile_file)],
    )
    assert "Profile created successfully." in result.output
    return _find_row(
        _json_rows(_invoke(runner, ["admin", "profiles", "ls", "--json"])),
        "name",
        profile_name,
    )


def test_authentication_lifecycle_for_a_regular_user(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,    # pylint: disable=W0613
    server_config: tuple[str, int, str, str],    # pylint: disable=W0613
    memory_keyring: dict[tuple[str, str], str],    # pylint: disable=W0613
) -> None:
    """A regular user can inspect, rotate, and revoke their own session."""
    runner = CliRunner()
    _configure_server(runner, server_config)
    _admin_login(runner, server_config)

    username = f"cli-auth-{uuid4().hex[:12]}"
    password = "initial-integration-password"
    user = _create_user(runner, tmp_path, username, password)
    user_id = str(user["id"])

    login_result = _login(runner, username, password)
    assert "Login successful" in login_result.output
    status_result = _invoke(runner, ["auth", "status", "--json"])
    status = cast(dict[str, object], _json_value(status_result))
    assert status["session"] == "active"
    assert cast(dict[str, object], status["user"])["username"] == username
    access_token = token_store.get_access_token(server_config[0], server_config[1])
    assert access_token
    assert access_token not in status_result.output

    new_password = "rotated-integration-password"
    change_result = _invoke(
        runner,
        ["auth", "password-chg"],
        input_text=f"{password}\n{new_password}\n{new_password}\n",
    )
    assert "Password changed." in change_result.output
    assert password not in change_result.output
    assert new_password not in change_result.output

    logout_result = _invoke(runner, ["auth", "logout"])
    assert "already inactive" in logout_result.output
    assert token_store.get_access_token(server_config[0], server_config[1]) is None
    inactive = _invoke(runner, ["auth", "status", "--json"])
    assert cast(dict[str, object], _json_value(inactive))["session"] == "inactive"
    _invoke(runner, ["auth", "status", "--check"], exit_code=1)

    _login(runner, username, new_password)
    relogin_logout_result = _invoke(runner, ["auth", "logout"])
    assert "Logout successful" in relogin_logout_result.output
    _admin_login(runner, server_config)
    _invoke(runner, ["admin", "users", "delete", "--user", user_id])


def test_admin_user_and_profile_workflow(
    tmp_path: Path,
    server_config: tuple[str, int, str, str],
    memory_keyring: dict[tuple[str, str], str],    # pylint: disable=W0613
) -> None:
    """Admins can create, edit, assign, unassign, and revoke user access."""
    runner = CliRunner()
    _configure_server(runner, server_config)
    _admin_login(runner, server_config)

    profile_name = f"cli-profile-{uuid4().hex[:12]}"
    profile = _create_profile(runner, tmp_path, profile_name)
    profile_id = _int_field(profile, "id")

    profile_details = cast(
        dict[str, object],
        _json_value(
            _invoke(
                runner,
                ["admin", "profiles", "get", "--profile", str(profile_id), "--json"],
            )
        ),
    )
    assert profile_details["name"] == profile_name

    updated_profile_name = f"{profile_name}-updated"
    profile_update_file = tmp_path / "profile-update.json"
    _write_json(
        profile_update_file,
        {
            "name": updated_profile_name,
            "default_duration": "2h",
            "maximum_duration": "6h",
            "networks": ["10.0.0.0/24"],
        },
    )
    _invoke(
        runner,
        [
            "admin", "profiles", "update", "--profile", str(profile_id),
            "--file", str(profile_update_file),
        ],
    )
    updated_profile = cast(
        dict[str, object],
        _json_value(
            _invoke(
                runner,
                ["admin", "profiles", "get", "--profile", str(profile_id), "--json"],
            )
        ),
    )
    assert updated_profile["name"] == updated_profile_name
    assert updated_profile["default_duration"] == "2h"

    username = f"cli-admin-{uuid4().hex[:12]}"
    user = _create_user(runner, tmp_path, username, "admin-workflow-password")
    user_id = str(user["id"])
    user_details = cast(
        dict[str, object],
        _json_value(_invoke(runner, ["admin", "users", "get", user_id, "--json"])),
    )
    assert user_details["username"] == username

    new_email = f"{username}-updated@example.test"
    user_update_file = tmp_path / "user-update.json"
    _write_json(user_update_file, {"email": new_email})
    _invoke(
        runner,
        [
            "admin", "users", "update", "--user", user_id,
            "--file", str(user_update_file),
        ],
    )
    updated_user = cast(
        dict[str, object],
        _json_value(_invoke(runner, ["admin", "users", "get", user_id, "--json"])),
    )
    assert updated_user["email"] == new_email

    _invoke(
        runner,
        [
            "admin", "users", "assign", "--user", user_id,
            "--profile", str(profile_id),
        ],
    )
    users_with_profile = _json_rows(
        _invoke(
            runner,
            ["admin", "users", "ls", "--profile", str(profile_id), "--json"],
        )
    )
    assert any(row.get("id") == user_id for row in users_with_profile)
    profiles_for_user = _json_rows(
        _invoke(
            runner,
            ["admin", "profiles", "ls", "--user", user_id, "--json"],
        )
    )
    assert any(row.get("id") == profile_id for row in profiles_for_user)

    _invoke(
        runner,
        [
            "admin", "users", "unassign", "--user", user_id,
            "--profile", str(profile_id),
        ],
    )
    _invoke(runner, ["admin", "users", "delete", "--user", user_id])
    delete_profile = _invoke(
        runner,
        ["admin", "profiles", "delete", "--profile", str(profile_id)],
        input_text=f"{updated_profile_name}\n",
    )
    assert "revoked successfully" in delete_profile.output


def test_user_and_admin_resource_workflow(
    tmp_path: Path,
    server_config: tuple[str, int, str, str],
    memory_keyring: dict[tuple[str, str], str],    # pylint: disable=W0613
) -> None:
    """Users manage owned resources while admins inspect and revoke them."""
    runner = CliRunner()
    _configure_server(runner, server_config)
    _admin_login(runner, server_config)

    username = f"cli-resource-{uuid4().hex[:12]}"
    user_password = "resource-workflow-password"
    user = _create_user(runner, tmp_path, username, user_password)
    user_id = str(user["id"])
    profile_name = f"cli-resource-profile-{uuid4().hex[:12]}"
    profile = _create_profile(runner, tmp_path, profile_name)
    profile_id = _int_field(profile, "id")
    _invoke(
        runner,
        [
            "admin", "users", "assign", "--user", user_id,
            "--profile", str(profile_id),
        ],
    )

    _login(runner, username, user_password)
    overview = cast(
        dict[str, object],
        _json_value(_invoke(runner, ["user", "get", "--json"])),
    )
    assert cast(dict[str, object], overview["user"])["id"] == user_id
    profiles = _json_rows(_invoke(runner, ["user", "profiles", "ls", "--json"]))
    assert any(row.get("id") == profile_id for row in profiles)
    assigned_profile = cast(
        dict[str, object],
        _json_value(
            _invoke(
                runner,
                ["user", "profiles", "get", "--id", str(profile_id), "--json"],
            )
        ),
    )
    assert assigned_profile["name"] == profile_name

    device_name = f"cli-device-{uuid4().hex[:12]}"
    device_file = tmp_path / "device.json"
    _write_json(
        device_file,
        {
            "name": device_name,
            "public_key": base64.b64encode(os.urandom(32)).decode("ascii"),
        },
    )
    _invoke(runner, ["user", "devices", "add", "--file", str(device_file)])
    device = _find_row(
        _json_rows(_invoke(runner, ["user", "devices", "ls", "--json"])),
        "name",
        device_name,
    )
    device_id = _int_field(device, "id")
    device_details = cast(
        dict[str, object],
        _json_value(
            _invoke(runner, ["user", "devices", "get", "--id", str(device_id), "--json"])
        ),
    )
    assert device_details["name"] == device_name

    second_device_name = f"cli-device-delete-{uuid4().hex[:12]}"
    second_device_file = tmp_path / "second-device.json"
    _write_json(
        second_device_file,
        {"name": second_device_name, "public_key": f"public-key-{uuid4().hex}"},
    )
    _invoke(runner, ["user", "devices", "add", "--file", str(second_device_file)])
    second_device = _find_row(
        _json_rows(_invoke(runner, ["user", "devices", "ls", "--json"])),
        "name",
        second_device_name,
    )
    _invoke(
        runner,
        ["user", "devices", "delete", "--id", str(second_device["id"])],
        input_text="y\n",
    )

    lease_file = tmp_path / "lease.json"
    _write_json(lease_file, {"device_id": device_id, "profile_id": profile_id})
    _invoke(runner, ["user", "leases", "create", "--file", str(lease_file)])
    first_lease = _find_row(
        _json_rows(_invoke(runner, ["user", "leases", "ls", "--json"])),
        "device_id",
        device_id,
    )
    first_lease_id = _int_field(first_lease, "id")
    first_lease_details = cast(
        dict[str, object],
        _json_value(
            _invoke(
                runner,
                ["user", "leases", "get", "--id", str(first_lease_id), "--json"],
            )
        ),
    )
    assert first_lease_details["status"] == "active"
    _invoke(
        runner,
        ["user", "leases", "revoke", "--id", str(first_lease_id)],
        input_text="y\n",
    )

    _invoke(runner, ["user", "leases", "create", "--file", str(lease_file)])
    active_lease = _find_row(
        _json_rows(_invoke(runner, ["user", "leases", "ls", "--json"])),
        "status",
        "active",
    )
    active_lease_id = _int_field(active_lease, "id")

    _invoke(runner, ["auth", "logout"])

    _admin_login(runner, server_config)
    admin_device = _find_row(
        _json_rows(_invoke(runner, ["admin", "devices", "ls", "--json"])),
        "id",
        device_id,
    )
    assert admin_device["user_id"] == user_id
    _invoke(runner, ["admin", "devices", "get", "--device", str(device_id)])
    device_update_file = tmp_path / "admin-device-update.json"
    updated_device_name = f"{device_name}-admin-updated"
    _write_json(device_update_file, {"name": updated_device_name})
    _invoke(
        runner,
        [
            "admin", "devices", "update", "--device", str(device_id),
            "--file", str(device_update_file),
        ],
    )

    admin_lease = cast(
        dict[str, object],
        _json_value(
            _invoke(
                runner,
                ["admin", "leases", "get", "--lease", str(active_lease_id), "--json"],
            )
        ),
    )
    assert admin_lease["user_id"] == user_id
    _invoke(
        runner,
        ["admin", "leases", "ls", "--user", user_id, "--json"],
    )
    _invoke(
        runner,
        ["admin", "leases", "revoke", "--lease", str(active_lease_id)],
        input_text="y\n",
    )
    revoked_lease = cast(
        dict[str, object],
        _json_value(
            _invoke(
                runner,
                ["admin", "leases", "get", "--lease", str(active_lease_id), "--json"],
            )
        ),
    )
    assert revoked_lease["status"] == "revoked"

    _invoke(
        runner,
        ["admin", "devices", "block", "--device", str(device_id)],
        input_text="y\n",
    )
    _invoke(
        runner,
        ["admin", "devices", "delete", "--device", str(device_id)],
        input_text="y\n",
    )
    _invoke(
        runner,
        ["admin", "users", "unassign", "--user", user_id,
         "--profile", str(profile_id)],
    )
    _invoke(runner, ["admin", "users", "delete", "--user", user_id])
    _invoke(
        runner,
        ["admin", "profiles", "delete", "--profile", str(profile_id)],
        input_text=f"{profile_name}\n",
    )


def test_global_configuration_workflow_applies_only_inside_compose(
    tmp_path: Path,
    server_config: tuple[str, int, str, str],
    memory_keyring: dict[tuple[str, str], str],    # pylint: disable=W0613
) -> None:
    """Global configuration can be read, validated, compared, and applied."""
    runner = CliRunner()
    _configure_server(runner, server_config)
    _admin_login(runner, server_config)

    current = cast(
        dict[str, object],
        _json_value(_invoke(runner, ["global-config", "get", "--json"])),
    )
    assert cast(dict[str, object], current["app"])

    candidate_admin_password = "integration-global-config-password"
    candidate = {
        "app": {
            "environment": "development",
            "debug": False,
            "secret_key_file": "/run/secrets/flask_secret_key",
            "log_level": "warning",
        },
        "server": {"host": "127.0.0.1", "port": 8080},
        "auth": {
            "mode": "internal",
            "cookie_name": "ttl-lama_session",
            "admin": {
                "username": server_config[2],
                "password": candidate_admin_password,
            },
        },
        "database": {"type": "sqlite", "path": ":memory:", "schema": "public"},
        "security": {
            "enforce_secure_connection": False,
            "session_cookie_name": "session",
            "session_cookie_httponly": True,
            "session_cookie_secure": False,
            "session_cookie_samesite": "Lax",
            "session_cookie_path": "/",
            "session_lifetime": 3600,
        },
    }
    candidate_file = tmp_path / "candidate.json"
    _write_json(candidate_file, candidate)

    diff_result = _invoke(
        runner,
        ["global-config", "diff", "--file", str(candidate_file)],
    )
    assert "app.log_level" in diff_result.output
    validate_result = _invoke(
        runner,
        ["global-config", "validate", "--file", str(candidate_file)],
    )
    assert "Configuration is valid." in validate_result.output

    apply_result = _invoke(
        runner,
        ["global-config", "apply", "--file", str(candidate_file)],
        input_text="y\n",
    )
    assert "Configuration applied." in apply_result.output
    assert candidate_admin_password not in apply_result.output
    persisted = cast(
        dict[str, object],
        _json_value(_invoke(runner, ["global-config", "get", "--json"])),
    )
    persisted_app = cast(dict[str, object], persisted["app"])
    assert persisted_app["log_level"] == "warning"
    assert persisted_app["secret_key_file"] == "/run/secrets/flask_secret_key"
