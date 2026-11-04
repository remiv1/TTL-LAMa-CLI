"""Common utilities and base classes for TTL-LAMa CLI drivers.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from abc import ABC, abstractmethod

class VPNDriver(ABC):
    """Base class for VPN drivers in TTL-LAMa CLI."""

    @abstractmethod
    def list_leases(self, device_id: str | None = None) -> list[dict[str, str]]:
        """List leases, optionally filtered by device ID."""
        raise NotImplementedError

    @abstractmethod
    def get_lease(self, lease_id: str) -> dict[str, str]:
        """Retrieve a lease by its ID."""
        raise NotImplementedError

    def create_lease(self, lease_data: dict[str, str]) -> int:
        """Create a new lease with the given data."""
        raise NotImplementedError

    @abstractmethod
    def apply_lease(self, file_path: str) -> None:
        """Apply a lease from a file."""
        raise NotImplementedError

    @abstractmethod
    def revoke_lease(self, lease_id: str) -> None:
        """Revoke a lease by its ID."""
        raise NotImplementedError
