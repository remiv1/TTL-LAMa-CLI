"""Tests for the TTL-LAMa CLI."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands import config as config_commands
from ttlama_cli.commands.backend.wireguard import peers as wireguard_commands
from ttlama_cli.drivers._common import RunResult, VPNLease, VPNLeaseState
from ttlama_cli.objects import HTTPMethod, SpecificRequest

def test_help_is_available() -> None:
    """Test that the help option is available for the CLI."""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output

def test_internal_login_help_is_available() -> None:
    """Test that the help option is available for the internal login command."""
    result = CliRunner().invoke(
        app,
        ["auth", "login", "internal", "--help"],
    )

    assert result.exit_code == 0
    assert "--user" in result.output

def test_admin_help_is_available() -> None:
    """Test that the help option is available for the admin command."""
    result = CliRunner().invoke(
        app,
        ["admin", "--help"],
    )

    assert result.exit_code == 0
    assert "Usage:" in result.output

def test_admin_users_help_is_available() -> None:
    """Test that the help option is available for the admin users command."""
    result = CliRunner().invoke(
        app,
        ["admin", "users", "--help"],
    )

    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_wireguard_lease_list_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON output contains the interface and all peer lease fields."""
    driver = Mock(
        list_leases=Mock(return_value=[VPNLeaseState(
            interface="wg0",
            identity="public-key",
            addresses=("10.101.0.0/24", "10.102.0.0/24"),
        )]),
    )
    driver_factory = Mock(return_value=driver)
    monkeypatch.setattr(wireguard_commands, "WireGuardDriver", driver_factory)

    result = CliRunner().invoke(app, ["backend", "wg", "leases", "ls", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == [{
        "interface": "wg0",
        "identity": "public-key",
        "addresses": ["10.101.0.0/24", "10.102.0.0/24"],
    }]
    driver_factory.assert_called_once_with("all")


def test_wireguard_lease_list_empty_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """YAML output for an empty list remains an empty collection."""
    driver = Mock(list_leases=Mock(return_value=[]))
    monkeypatch.setattr(
        wireguard_commands,
        "WireGuardDriver",
        Mock(return_value=driver),
    )

    result = CliRunner().invoke(app, ["backend", "wg", "leases", "ls", "--yaml"])

    assert result.exit_code == 0
    assert result.output.strip() == "[]"


def test_wireguard_lease_list_interface_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The selected interface is passed to the driver and shown in the table."""
    driver = Mock(list_leases=Mock(return_value=[VPNLeaseState(
        interface="wg0",
        identity="public-key",
        addresses=("10.101.0.0/24",),
    )]))
    driver_factory = Mock(return_value=driver)
    monkeypatch.setattr(wireguard_commands, "WireGuardDriver", driver_factory)

    result = CliRunner().invoke(
        app,
        ["backend", "wg", "leases", "ls", "--interface", "wg0"],
    )

    assert result.exit_code == 0
    assert "wg0" in result.output
    assert "public-key" in result.output
    driver_factory.assert_called_once_with("wg0")


def test_wireguard_lease_list_rejects_multiple_output_formats() -> None:
    """JSON and YAML output options cannot be combined."""
    result = CliRunner().invoke(
        app,
        ["backend", "wg", "leases", "ls", "--json", "--yaml"],
    )

    assert result.exit_code == 1
    assert "Choose only one output option" in result.output


def test_wireguard_lease_get_returns_json_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Get reads the full lease from stdin and returns the peer state."""
    payload = {
        "interface": "wg0",
        "lease_id": "lease-1",
        "device_id": "device-1",
        "public_key": "public-key",
        "addresses": ["10.101.0.0/24"],
    }
    state = VPNLeaseState(
        interface="wg0",
        identity="public-key",
        addresses=("10.101.0.0/24",),
    )
    driver = Mock(get_lease=Mock(return_value=state))
    driver_factory = Mock(return_value=driver)
    monkeypatch.setattr(wireguard_commands, "WireGuardDriver", driver_factory)

    result = CliRunner().invoke(
        app,
        ["backend", "wg", "leases", "get", "--lease", "-", "--json"],
        input=json.dumps(payload),
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "interface": "wg0",
        "identity": "public-key",
        "addresses": ["10.101.0.0/24"],
    }
    driver_factory.assert_called_once_with("wg0")
    driver.get_lease.assert_called_once_with("public-key", "wg0")


def test_wireguard_lease_get_missing_returns_null_and_check_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing lease returns null and --check signals the absence."""
    payload = {
        "interface": "wg0",
        "lease_id": "lease-1",
        "device_id": "device-1",
        "public_key": "public-key",
        "addresses": ["10.101.0.0/24"],
    }
    driver = Mock(get_lease=Mock(return_value=None))
    monkeypatch.setattr(
        wireguard_commands,
        "WireGuardDriver",
        Mock(return_value=driver),
    )

    result = CliRunner().invoke(
        app,
        [
            "backend", "wg", "leases", "get", "--lease", "-", "--json", "--check",
        ],
        input=json.dumps(payload),
    )

    assert result.exit_code == 1
    assert json.loads(result.output) is None


def test_wireguard_lease_apply_reads_yaml_and_returns_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply accepts YAML from stdin and returns a JSON status object."""
    payload = (
        "interface: wg0\n"
        "lease_id: lease-1\n"
        "device_id: device-1\n"
        "public_key: public-key\n"
        "addresses:\n"
        "  - 10.101.0.0/24\n"
    )
    driver = Mock(apply_lease=Mock(return_value=RunResult(0, "", "")))
    driver_factory = Mock(return_value=driver)
    monkeypatch.setattr(wireguard_commands, "WireGuardDriver", driver_factory)

    result = CliRunner().invoke(
        app,
        ["backend", "wg", "leases", "apply", "--lease", "-"],
        input=payload,
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "success": True,
        "operation": "apply",
        "interface": "wg0",
        "identity": "public-key",
    }
    driver_factory.assert_called_once_with("wg0")
    driver.apply_lease.assert_called_once_with(VPNLease(
        lease_id="lease-1",
        device_id="device-1",
        public_key="public-key",
        addresses=("10.101.0.0/24",),
    ))


def test_wireguard_lease_delete_returns_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delete revokes the peer and returns a JSON status object."""
    payload = {
        "interface": "wg0",
        "lease_id": "lease-1",
        "device_id": "device-1",
        "public_key": "public-key",
        "addresses": ["10.101.0.0/24"],
    }
    driver = Mock(revoke_lease=Mock(return_value=RunResult(0, "", "")))
    monkeypatch.setattr(
        wireguard_commands,
        "WireGuardDriver",
        Mock(return_value=driver),
    )

    result = CliRunner().invoke(
        app,
        ["backend", "wg", "leases", "delete", "--lease", "-"],
        input=json.dumps(payload),
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "success": True,
        "operation": "delete",
        "interface": "wg0",
        "identity": "public-key",
    }
    driver.revoke_lease.assert_called_once_with(VPNLease(
        lease_id="lease-1",
        device_id="device-1",
        public_key="public-key",
        addresses=("10.101.0.0/24",),
    ))


def test_wireguard_lease_mutation_rejects_all_interfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation input must select one specific WireGuard interface."""
    payload = {
        "interface": "all",
        "lease_id": "lease-1",
        "device_id": "device-1",
        "public_key": "public-key",
        "addresses": ["10.101.0.0/24"],
    }
    driver_factory = Mock()
    monkeypatch.setattr(wireguard_commands, "WireGuardDriver", driver_factory)

    result = CliRunner().invoke(
        app,
        ["backend", "wg", "leases", "apply", "--lease", "-"],
        input=json.dumps(payload),
    )

    assert result.exit_code == 1
    assert "specific interface" in result.output
    driver_factory.assert_not_called()


def test_global_config_group_is_registered() -> None:
    """The global configuration group is a root-level CLI command."""
    result = CliRunner().invoke(app, ["global-config", "--help"])

    assert result.exit_code == 0
    assert "get" in result.output
    assert "diff" in result.output
    assert "validate" in result.output
    assert "apply" in result.output


def test_global_config_get_json_returns_raw_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON output preserves the server configuration document without a wrapper."""
    configuration = {"app": {"environment": "production", "secret_key": "[REDACTED]"}}
    request_api = Mock(return_value=configuration)
    monkeypatch.setattr(
        config_commands,
        "get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(config_commands, "request_api", request_api)

    result = CliRunner().invoke(app, ["global-config", "get", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == configuration
    request = request_api.call_args.kwargs["specific_request"]
    assert isinstance(request, SpecificRequest)
    assert request.method is HTTPMethod.GET
    assert request.endpoint == "global-config"


def test_global_config_diff_shows_added_and_removed_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diff represents a changed leaf as a removal and an addition."""
    file_path = tmp_path / "candidate.yml"
    file_path.write_text("app:\n  environment: staging\n", encoding="utf-8")
    request_api = Mock(
        side_effect=[
            {
                "app": {
                    "environment": "production"
                },
            },
            {
                "valid": True,
                "errors": [],
            },
            {"unchanged_secrets": []},
        ],
    )
    monkeypatch.setattr(
        config_commands,
        "get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(config_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["global-config", "diff", "--file", str(file_path)],
    )

    assert result.exit_code == 0
    assert "Removed" in result.output
    assert "Added" in result.output
    assert "app.environment" in result.output


def test_global_config_apply_dry_run_never_posts_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dry-run validates and displays changes without persisting them."""
    file_path = tmp_path / "candidate.yml"
    file_path.write_text("app:\n  environment: staging\n", encoding="utf-8")
    request_api = Mock(
        side_effect=[
            {
                "app": {
                    "environment": "production",
                },
            },
            {
                "valid": True,
                "errors": [],
            },
            {"unchanged_secrets": []},
        ],
    )
    monkeypatch.setattr(
        config_commands,
        "get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(config_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["global-config", "apply", "--file", str(file_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "no changes were applied" in result.output
    assert request_api.call_count == 3
    assert all(
        call.kwargs["specific_request"].endpoint != "global-config/apply"
        for call in request_api.call_args_list
    )


def test_global_config_validate_reports_server_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate prints server-side errors and exits unsuccessfully."""
    file_path = tmp_path / "candidate.yml"
    file_path.write_text("app:\n  environment: unknown\n", encoding="utf-8")
    request_api = Mock(return_value={"valid": False, "errors": ["app.environment: invalid"]})
    monkeypatch.setattr(
        config_commands,
        "get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(config_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["global-config", "validate", "--file", str(file_path)],
    )

    assert result.exit_code == 1
    assert "app.environment: invalid" in result.output
    assert request_api.call_args.kwargs["specific_request"].endpoint == "global-config/validate"


def test_global_config_apply_confirms_and_reports_restart_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirmed apply posts the candidate and reports restart and mount state."""
    file_path = tmp_path / "candidate.yml"
    file_path.write_text("app:\n  environment: staging\n", encoding="utf-8")
    request_api = Mock(
        side_effect=[
            {"app": {"environment": "production"}},
            {"valid": True, "errors": []},
            {"unchanged_secrets": []},
            {"applied": True, "restart_required": True, "warning": "not mounted"},
        ],
    )
    monkeypatch.setattr(
        config_commands,
        "get_server_and_token",
        lambda: ("https://server.example", 8443, "access-token"),
    )
    monkeypatch.setattr(config_commands, "request_api", request_api)

    result = CliRunner().invoke(
        app,
        ["global-config", "apply", "--file", str(file_path)],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Restart the server" in result.output
    assert "not mounted" in result.output
    apply_request = request_api.call_args_list[-1].kwargs["specific_request"]
    assert apply_request.method is HTTPMethod.POST
    assert apply_request.endpoint == "global-config/apply"
    assert apply_request.json_body == {"app": {"environment": "staging"}}
