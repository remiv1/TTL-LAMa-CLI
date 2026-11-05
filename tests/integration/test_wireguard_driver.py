"""Integration tests for the WireGuard driver."""

import subprocess

import pytest

from ttlama_cli.drivers.wireguard import WireGuardDriver
from ttlama_cli.drivers._common import VPNLease, VPNLeaseState

def _generate_public_key() -> str:
    private_key = subprocess.run(
        ["wg", "genkey"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    public_key = subprocess.run(
        ["wg", "pubkey"],
        input=private_key,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return public_key

def test_create_lease(
    driver: WireGuardDriver,
    interface: str,
    public_key: str,
) -> None:
    """Test creating a VPN lease with the WireGuard driver."""
    lease = VPNLease(
        lease_id="lease-1",
        device_id="device-1",
        public_key=public_key,
        addresses=(
            "10.101.0.0/24",
            "10.102.0.0/24",
            "10.103.0.0/24",
        ),
    )

    result = driver.create_lease(lease)

    assert result.returncode == 0

    state = driver.get_lease(public_key)

    assert state == VPNLeaseState(
        interface=interface,
        identity=public_key,
        addresses=(
            "10.101.0.0/24",
            "10.102.0.0/24",
            "10.103.0.0/24",
        ),
    )

def test_apply_lease_replaces_addresses(
    driver: WireGuardDriver,
    interface: str,
    public_key: str,
) -> None:
    """Test that applying a VPN lease replaces the existing addresses."""
    initial = VPNLease(
        lease_id="lease-1",
        device_id="device-1",
        public_key=public_key,
        addresses=("10.101.0.0/24",),
    )

    driver.create_lease(initial)

    updated = VPNLease(
        lease_id="lease-1",
        device_id="device-1",
        public_key=public_key,
        addresses=(
            "10.102.0.0/24",
            "10.103.0.0/24",
        ),
    )

    result = driver.apply_lease(updated)

    assert result.returncode == 0
    assert driver.get_lease(public_key) == VPNLeaseState(
        interface=interface,
        identity=public_key,
        addresses=(
            "10.102.0.0/24",
            "10.103.0.0/24",
        ),
    )

def test_revoke_lease(
    driver: WireGuardDriver,
    public_key: str,
) -> None:
    """Test revoking a VPN lease with the WireGuard driver."""
    lease = VPNLease(
        lease_id="lease-1",
        device_id="device-1",
        public_key=public_key,
        addresses=("10.101.0.0/24",),
    )

    driver.create_lease(lease)

    assert driver.get_lease(public_key) is not None

    result = driver.revoke_lease(lease)

    assert result.returncode == 0
    assert driver.get_lease(public_key) is None

def test_list_leases_across_all_interfaces(
    wg_interfaces: tuple[str, ...],
    all_interfaces_driver: WireGuardDriver,
) -> None:
    """Test listing VPN leases across all interfaces."""
    first_interface, second_interface = wg_interfaces
    first_key = _generate_public_key()
    second_key = _generate_public_key()

    first_driver = WireGuardDriver(first_interface)
    second_driver = WireGuardDriver(second_interface)

    first_driver.create_lease(
        VPNLease(
            lease_id="lease-1",
            device_id="device-1",
            public_key=first_key,
            addresses=("10.101.0.0/24",),
        )
    )

    second_driver.create_lease(
        VPNLease(
            lease_id="lease-2",
            device_id="device-2",
            public_key=second_key,
            addresses=(
                "10.102.0.0/24",
                "10.103.0.0/24",
            ),
        )
    )

    leases = all_interfaces_driver.list_leases()
    assert any(lease.identity == first_key for lease in leases)
    assert any(lease.identity == second_key for lease in leases)

@pytest.mark.parametrize(
    "operation",
    [
        "create_lease",
        "apply_lease",
        "revoke_lease",
    ],
)
def test_write_operations_require_specific_interface(
    all_interfaces_driver: WireGuardDriver,
    public_key: str,
    operation: str,
) -> None:
    """Reject write operations when the driver targets all interfaces."""

    lease = VPNLease(
        lease_id="lease-1",
        device_id="device-1",
        public_key=public_key,
        addresses=("10.101.0.1/32",),
    )

    method = getattr(all_interfaces_driver, operation)

    with pytest.raises(
        ValueError,
        match="specific WireGuard interface",
    ):
        method(lease)
