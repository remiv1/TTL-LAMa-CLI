"""Common utilities and base classes for TTL-LAMa CLI drivers.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class VPNLease:
    """Represents a VPN lease.

    :param lease_id: ID of the lease.
    :type lease_id: str
    :param device_id: ID of the device associated with the lease.
    :type device_id: str
    :param public_key: Public key of the device.
    :type public_key: str
    :param addresses: IP addresses assigned to the device.
    :type addresses: tuple[str, ...]
    """

    lease_id: str
    device_id: str
    public_key: str
    addresses: tuple[str, ...]

@dataclass(frozen=True)
class VPNLeaseState:
    """Represents the state of a VPN lease.

    :param interface: Interface associated with the lease.
    :type interface: str
    :param identity: Identity of the lease (e.g., public key).
    :type identity: str
    :param addresses: IP addresses assigned to the lease.
    :type addresses: tuple[str, ...]
    """
    interface: str
    identity: str
    addresses: tuple[str, ...]

@dataclass(frozen=True)
class RunResult:
    """Represents the result of running a command.

    :param returncode: Return code of the command.
    :type returncode: int
    :param stdout: Standard output of the command.
    :type stdout: str
    :param stderr: Standard error of the command.
    :type stderr: str
    """

    returncode: int
    stdout: str
    stderr: str


class VPNDriver(ABC):
    """Base class for VPN drivers in TTL-LAMa CLI."""

    @abstractmethod
    def list_leases(self) -> list[VPNLeaseState]:
        """List leases.

        :return: List of leases as VPNLeaseState objects.
        :rtype: list[VPNLeaseState]
        """
        raise NotImplementedError

    @abstractmethod
    def get_lease(self, identity: str) -> VPNLeaseState | None:
        """Retrieve a lease by its identity.

        :param identity: Identity to identify the lease (e.g., public key).
        :type identity: str
        :return: Lease data as a VPNLeaseState object.
        :rtype: VPNLeaseState | None
        """
        raise NotImplementedError

    @abstractmethod
    def create_lease(self, lease_data: VPNLease) -> RunResult:
        """Create a new lease with the given data.

        :param lease_data: VPNLease object containing lease information.
        :type lease_data: VPNLease
        :return: Result of the lease creation as a RunResult object.
        :rtype: RunResult
        """
        raise NotImplementedError

    @abstractmethod
    def apply_lease(self, lease_data: VPNLease) -> RunResult:
        """Apply a lease from its data.

        :param lease_data: VPNLease object containing lease information to apply.
        :type lease_data: VPNLease
        :return: Result of applying the lease as a RunResult object.
        :rtype: RunResult
        """
        raise NotImplementedError

    @abstractmethod
    def revoke_lease(self, lease_data: VPNLease) -> RunResult:
        """Revoke a lease by its data.

        :param lease_data: VPNLease object containing lease information to revoke.
        :type lease_data: VPNLease
        :return: Result of the lease revocation as a RunResult object.
        :rtype: RunResult
        """
        raise NotImplementedError
