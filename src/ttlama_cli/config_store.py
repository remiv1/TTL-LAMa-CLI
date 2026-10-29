"""Configuration store for TTL-LAMa CLI.

This module provides functions to save and load the server URL configuration for the
TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from typing import cast, Any

import json
from pathlib import Path
from urllib.parse import urlsplit

from platformdirs import user_config_path

_INVALID_FILE_ERROR = "TTL-LAMa config file is invalid."


def config_file() -> Path:
    """Return the path to the TTL-LAMa CLI configuration file."""
    return user_config_path("ttlama", appauthor=False) / "config.json"

def _validate_server_url(url: str) -> None:
    """Validate the server URL."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Put a valid HTTP or HTTPS URL.")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("Put an adress without username or password")
    if parsed.query or parsed.fragment:
        raise ValueError("Put an URL without query or fragment.")

def _check_data(data: Any) -> tuple[str, int]:
    if not isinstance(data, dict):
        raise ValueError(_INVALID_FILE_ERROR)

    data = cast(dict[str, str], data)
    server_url = data.get("server_url")
    server_port = data.get("server_port")

    if not isinstance(server_url, str):
        raise ValueError(_INVALID_FILE_ERROR)

    if (
        not isinstance(server_port, int)
        or isinstance(server_port, bool)
        or not (1 <= server_port <= 65535)
    ):
        raise ValueError(_INVALID_FILE_ERROR)

    _validate_server_url(server_url)
    return server_url, server_port

def save_server_config(url: str, port: int) -> None:
    """Save the server URL and port to the TTL-LAMa CLI configuration file."""
    _validate_server_url(url)

    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "server_url": url.rstrip("/"),
                "server_port": port,
            },
            indent=2
        )
        + "\n",
        encoding="utf-8",
    )

def load_server_config() -> tuple[str, int]:
    """Load the server URL and port from the TTL-LAMa CLI configuration file."""
    path = config_file()
    if not path.exists():
        raise FileNotFoundError("TTL-LAMa config file does not exist.")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(_INVALID_FILE_ERROR) from error

    return _check_data(data)
