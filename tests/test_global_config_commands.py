"""Tests for global configuration CLI commands."""

from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml
from typer.testing import CliRunner

from ttlama_cli.cli import app
from ttlama_cli.commands import config as config_commands


SECRET_KEY = "flask-secret-value-that-must-not-be-displayed"
ADMIN_PASSWORD = "admin-password-that-must-not-be-displayed"
CURRENT_CONFIGURATION = {
    "app": {"secret_key": "[REDACTED]"},
    "auth": {"admin": {"password": "[REDACTED]"}},
}


def _write_candidate(path: Path, admin_password: str = ADMIN_PASSWORD) -> None:
    candidate = {
        "app": {"secret_key": SECRET_KEY},
        "auth": {"admin": {"password": admin_password}},
    }
    path.write_text(yaml.safe_dump(candidate, sort_keys=False), encoding="utf-8")


def _mock_global_config_requests(
    monkeypatch: pytest.MonkeyPatch,
    unchanged_secrets: list[str],
) -> Mock:
    request = Mock(
        side_effect=[
            CURRENT_CONFIGURATION,
            {"valid": True, "errors": []},
            {"unchanged_secrets": unchanged_secrets},
        ],
    )
    monkeypatch.setattr(config_commands, "_request_global_config", request)
    return request


def test_diff_treats_matching_redacted_secrets_as_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Matching direct secrets produce no diff and are never printed."""
    candidate_path = tmp_path / "config.yml"
    _write_candidate(candidate_path)
    request = _mock_global_config_requests(
        monkeypatch,
        ["app.secret_key", "auth.admin.password"],
    )

    result = CliRunner().invoke(
        app,
        ["global-config", "diff", "--file", str(candidate_path)],
    )

    assert result.exit_code == 0
    assert "Configuration is already up to date." in result.output
    assert SECRET_KEY not in result.output
    assert ADMIN_PASSWORD not in result.output
    assert request.call_args_list[2].args[1] == "/compare"


def test_diff_reports_changed_secret_without_displaying_its_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changed direct secrets appear as redacted changes."""
    candidate_path = tmp_path / "config.yml"
    changed_password = "new-password-that-must-not-be-displayed"
    _write_candidate(candidate_path, changed_password)
    _mock_global_config_requests(monkeypatch, ["app.secret_key"])

    result = CliRunner().invoke(
        app,
        ["global-config", "diff", "--file", str(candidate_path)],
    )

    assert result.exit_code == 0
    assert "auth.admin.password" in result.output
    assert "Removed" in result.output
    assert "Added" in result.output
    assert "[REDACTED]" in result.output
    assert SECRET_KEY not in result.output
    assert ADMIN_PASSWORD not in result.output
    assert changed_password not in result.output


def test_apply_does_not_apply_when_only_secrets_are_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unchanged redacted secret does not prompt or send an apply request."""
    candidate_path = tmp_path / "config.yml"
    _write_candidate(candidate_path)
    request = _mock_global_config_requests(
        monkeypatch,
        ["app.secret_key", "auth.admin.password"],
    )

    result = CliRunner().invoke(
        app,
        ["global-config", "apply", "--file", str(candidate_path)],
    )

    assert result.exit_code == 0
    assert "Configuration is already up to date." in result.output
    assert request.call_count == 3
    assert SECRET_KEY not in result.output
    assert ADMIN_PASSWORD not in result.output
