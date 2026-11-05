"""WireGuard driver for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import subprocess

from ._common import VPNDriver, VPNLease, VPNLeaseState, RunResult

class WireGuardDriver(VPNDriver):
    """WireGuard driver implementation for TTL-LAMa CLI."""

    def __init__(self, interface: str = "all"):
        self._interface = interface

    def _require_writable_interface(self) -> None:
        if self._interface == "all":
            raise ValueError("Operation requires a specific WireGuard interface, not 'all'.")

    def _run(self, args: list[str]) -> RunResult:
        try:
            output = subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
            )
            return RunResult(
                returncode=output.returncode,
                stdout=output.stdout,
                stderr=output.stderr,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed: {e.stderr}") from e

    def _get_peers(self) -> dict[str, dict[str, list[str]]]:
        output = self._run(["wg", "show", self._interface, "allowed-ips"])

        peers: dict[str, dict[str, list[str]]] = {}

        for line in output.stdout.splitlines():
            parts = line.split()
            if not parts:
                continue

            if self._interface != "all":
                parts.insert(0, self._interface)

            interface, public_key, *allowed_ips = parts
            peers.setdefault(interface, {})[public_key] = allowed_ips

        return peers

    def _set_peer(self, lease: VPNLease) -> RunResult:
        self._require_writable_interface()

        return self._run([
            "wg",
            "set",
            self._interface,
            "peer",
            lease.public_key,
            "allowed-ips",
            ",".join(lease.addresses),
        ])

    def _remove_peer(self, lease: VPNLease) -> RunResult:
        self._require_writable_interface()

        return self._run([
            "wg",
            "set",
            self._interface,
            "peer",
            lease.public_key,
            "remove",
        ])

    def list_leases(self) -> list[VPNLeaseState]:
        """List all VPN leases.

        :return: List of leases as VPNLeaseState objects.
        :rtype: list[VPNLeaseState]
        """
        leases = self._get_peers()
        lease_states: list[VPNLeaseState] = []

        for interface, peers in leases.items():
            for public_key, allowed_ips in peers.items():
                lease_states.append(VPNLeaseState(
                    interface=interface,
                    identity=public_key,
                    addresses=tuple(allowed_ips),
                ))

        return lease_states


    def get_lease(
        self,
        identity: str,
        interface: str | None = None
    ) -> VPNLeaseState | None:
        """Retrieve a lease by its public key.

        :param identity: Identity (e.g., public key) of the lease to retrieve.
        :type identity: str
        :param interface: Specific interface to look for the lease on.
        :type interface: str | None
        :return: Lease data as a VPNLeaseState object.
        :rtype: VPNLeaseState | None
        """
        peers = self._get_peers()

        for iface, peers in peers.items():
            if interface is not None and iface != interface:
                continue

            allowed_ips = peers.get(identity)

            if allowed_ips is not None:
                return VPNLeaseState(
                    interface=iface,
                    identity=identity,
                    addresses=tuple(allowed_ips),
                )
        return None

    def create_lease(self, lease_data: VPNLease) -> RunResult:
        """Create a new lease with the given data.

        :param lease_data: VPNLease object containing lease information.
        :type lease_data: VPNLease
        :return: Result of the lease creation as a RunResult object.
        :rtype: RunResult

        :raises ValueError: If the interface is set to 'all', which is not writable.
        """
        return self._set_peer(lease_data)

    def apply_lease(self, lease_data: VPNLease) -> RunResult:
        """Apply a lease from its data.

        :param lease_data: VPNLease object containing lease information to apply.
        :type lease_data: VPNLease
        :return: Result of applying the lease as a RunResult object.
        :rtype: RunResult

        :raises ValueError: If the interface is set to 'all', which is not writable.
        """
        return self._set_peer(lease_data)

    def revoke_lease(self, lease_data: VPNLease) -> RunResult:
        """Revoke a lease by its data.

        :param lease_data: VPNLease object containing lease information to revoke.
        :type lease_data: VPNLease
        :return: Result of the lease revocation as a RunResult object.
        :rtype: RunResult

        :raises ValueError: If the interface is set to 'all', which is not writable.
        """
        return self._remove_peer(lease_data)
