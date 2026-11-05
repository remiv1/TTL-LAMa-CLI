"""OpenVPN driver for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from ._common import VPNDriver, VPNLease, VPNLeaseState, RunResult

class OpenVPNDriver(VPNDriver):
    """OpenVPN driver implementation for TTL-LAMa CLI."""

    def list_leases(self) -> list[VPNLeaseState]:
        """List all VPN leases.
        
        :return: List of leases as VPNLeaseState objects.
        :rtype: list[VPNLeaseState]
        """
        raise NotImplementedError

    def get_lease(self, identity: str) -> VPNLeaseState | None:
        """Retrieve a lease by its identity.
        
        :param identity: Identity of the lease to retrieve.
        :type identity: str
        :return: Lease data as a VPNLeaseState object.
        :rtype: VPNLeaseState | None
        """
        raise NotImplementedError

    def create_lease(self, lease_data: VPNLease) -> RunResult:
        """Create a new lease with the given data.
        
        :param lease_data: VPNLease object containing lease information.
        :type lease_data: VPNLease
        :return: Result of the lease creation as a RunResult object.
        :rtype: RunResult
        """
        raise NotImplementedError

    def apply_lease(self, lease_data: VPNLease) -> RunResult:
        """Apply a lease from its data.
        
        :param lease_data: VPNLease object containing lease information to apply.
        :type lease_data: VPNLease
        :return: Result of applying the lease as a RunResult object.
        :rtype: RunResult
        """
        raise NotImplementedError

    def revoke_lease(self, lease_data: VPNLease) -> RunResult:
        """Revoke a lease by its data.
        
        :param lease_data: VPNLease object containing lease information to revoke.
        :type lease_data: VPNLease
        :return: Result of the lease revocation as a RunResult object.
        :rtype: RunResult
        """
        raise NotImplementedError
