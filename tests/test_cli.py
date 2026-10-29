"""Tests for the TTL-LAMa CLI."""

from typer.testing import CliRunner

from ttlama_cli.cli import app

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
