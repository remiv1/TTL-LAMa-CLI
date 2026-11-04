"""OpenVPN driver for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from ._common import VPNDriver

class OpenVPNDriver(VPNDriver):
    """OpenVPN driver implementation for TTL-LAMa CLI."""

    def list_leases(self, device_id: str | None = None) -> list[dict[str, str]]:
        """List leases, optionally filtered by device ID.
        
        :param device_id: Optional device ID to filter leases by.
        :type device_id: str | None
        :return: List of leases as dictionaries.
        :rtype: list[dict[str, str]]
        """
        raise NotImplementedError

    def get_lease(self, lease_id: str) -> dict[str, str]:
        """Retrieve a lease by its ID.
        
        :param lease_id: ID of the lease to retrieve.
        :type lease_id: str
        :return: Lease data as a dictionary.
        :rtype: dict[str, str]
        """
        raise NotImplementedError

    def create_lease(self, lease_data: dict[str, str]) -> int:
        """Create a new lease with the given data.
        
        :param lease_data: Data for the new lease.
        :type lease_data: dict[str, str]
        :return: ID of the created lease.
        :rtype: int
        """
        raise NotImplementedError

    def apply_lease(self, file_path: str) -> None:
        """Apply a lease from a file.
        
        :param file_path: Path to the lease file.
        :type file_path: str
        """
        raise NotImplementedError

    def revoke_lease(self, lease_id: str) -> None:
        """Revoke a lease by its ID.
        
        :param lease_id: ID of the lease to revoke.
        :type lease_id: str
        """
        raise NotImplementedError
