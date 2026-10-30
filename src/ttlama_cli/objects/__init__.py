"""Module for TTL-LAMa CLI objects.

.. classes::
    - `HTTPMethod`: Enumeration of HTTP methods.
    - `SpecificRequest`: Class representing a specific HTTP request.
    - `ServerParameters`: Class representing server parameters.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""

from .requests import HTTPMethod, SpecificRequest, ServerParameters

__all__ = [
    "HTTPMethod",
    "SpecificRequest",
    "ServerParameters",
]
