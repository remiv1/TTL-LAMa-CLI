"""Config_store fixture for TTL-LAMa CLI tests."""

from pathlib import Path

import pytest

from ttlama_cli import config_store

@pytest.fixture
def config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Fixture to provide a temporary configuration file path."""
    path = tmp_path / "config.json"
    monkeypatch.setattr(config_store, "config_file", lambda: path)
    return path
