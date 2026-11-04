"""WireGuard driver for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from ._common import VPNDriver

class WireGuardDriver(VPNDriver):
    """WireGuard driver implementation for TTL-LAMa CLI."""

    def list_leases(self, device_id: str | None = None) -> list[dict[str, str]]:
        raise NotImplementedError

    def get_lease(self, lease_id: str) -> dict[str, str]:
        raise NotImplementedError

    def create_lease(self, lease_data: dict[str, str]) -> int:
        raise NotImplementedError

    def apply_lease(self, file_path: str) -> None:
        raise NotImplementedError

    def revoke_lease(self, lease_id: str) -> None:
        raise NotImplementedError
