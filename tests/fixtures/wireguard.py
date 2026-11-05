"""WireGuard test fixtures for TTL-LAMa CLI."""
from __future__ import annotations

from collections.abc import Generator
import subprocess

import pytest

from ttlama_cli.drivers.wireguard import WireGuardDriver

TEST_INTERFACES = (
    "ttlama-test0",
    "ttlama-test1",
)

def _run(*args: str) -> None:
    subprocess.run(
        list(args),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def wg_interfaces() -> Generator[tuple[str, ...], None, None]:
    """Provide a temporary WireGuard interface for testing."""
    created: list[str] = []

    for i in TEST_INTERFACES:
        _run("ip", "link", "add", i, "type", "wireguard")
        _run("ip", "link", "set", i, "up")
        created.append(i)

    try:
        yield TEST_INTERFACES
    finally:
        for i in reversed(created):
            _run("ip", "link", "delete", i)

@pytest.fixture(params=TEST_INTERFACES, ids=lambda interface: f"interface-{interface}")
def interface(request: pytest.FixtureRequest) -> str:
    """Provide a single WireGuard interface for testing."""
    return request.param

@pytest.fixture
def driver(
    wg_interfaces: tuple[str, ...],   # pylint: disable=W0621
    interface: str,   # pylint: disable=W0621
) -> WireGuardDriver:
    """Provide a WireGuard driver instance for testing."""
    assert interface in wg_interfaces
    return WireGuardDriver(interface)

@pytest.fixture
def all_interfaces_driver(
    wg_interfaces: tuple[str, ...],   # pylint: disable=W0621
) -> WireGuardDriver:
    """Provide a WireGuard driver instance for all interfaces."""
    assert wg_interfaces
    return WireGuardDriver("all")

@pytest.fixture
def public_key() -> str:
    """Provide a WireGuard public key for testing."""
    private = subprocess.run(
        ["wg", "genkey"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    public = subprocess.run(
        ["wg", "pubkey"],
        input=private,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    return public
