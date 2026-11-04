"""Module installing drivers for TTL-LAMa CLI.
The drivers make the commutator work between the TTL-LAMa CLI and the backend implementations.
This contains abstractions for different VPN drivers used by the TTL-LAMa CLI. The abstractions
are declined into specific driver implementations like WireGuard or OpenVPN.

.. classes::
    - `WireGuardDriver`: First VPN driver implementation for TTL-LAMa CLI.
    - `OpenVPNDriver`: OpenVPN driver implementation for TTL-LAMa CLI. (Not implemented)

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from .wireguard import WireGuardDriver
from .openvpn import OpenVPNDriver

__all__ = [
    "WireGuardDriver",
    "OpenVPNDriver",
]
