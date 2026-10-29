"""Tests for TTL-LAMa CLI configuration store."""
import json
from pathlib import Path

import pytest

from ttlama_cli import config_store


def test_save_and_load_server_config(config_path: Path) -> None:    # pylint: disable=W0613
    """Test saving and loading server configuration."""
    config_store.save_server_config("https://serveur.example/", 8443)

    assert config_store.load_server_config() == (
        "https://serveur.example",
        8443,
    )


def test_load_missing_config_raises(config_path: Path) -> None:    # pylint: disable=W0613
    """Test that loading a missing configuration raises ValueError."""
    with pytest.raises(FileNotFoundError):
        config_store.load_server_config()


@pytest.mark.parametrize("port", [0, 65536, True])
def test_load_rejects_invalid_port(config_path: Path, port: object) -> None:
    """Test that loading a configuration with an invalid port raises ValueError."""
    config_path.write_text(
        json.dumps(
            {"server_url": "https://serveur.example", "server_port": port}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        config_store.load_server_config()


@pytest.mark.parametrize(
    "url",
    [
        "ftp://serveur.example",
        "http:///sans-hôte",
        "https://user:secret@serveur.example",
        "https://serveur.example/?token=secret",
    ],
)
def test_save_rejects_invalid_url(url: str) -> None:
    """Test that saving a configuration with an invalid URL raises ValueError."""
    with pytest.raises(ValueError):
        config_store.save_server_config(url, 8080)
