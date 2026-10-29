"""Exceptions for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
class TTLAMaCLIException(Exception):
    """Base exception for TTL-LAMa CLI."""
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "An error occurred in TTL-LAMa CLI."
        super().__init__(self.message)

class AuthenticationError(TTLAMaCLIException):
    """Raised when authentication fails."""
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Authentication failed."
        super().__init__(self.message)

class TokenStorageError(TTLAMaCLIException):
    """Raised when storing or retrieving tokens fails."""
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Token storage error."
        super().__init__(self.message)

class ServerConfigError(TTLAMaCLIException):
    """Raised when there is an issue with the server configuration."""
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Server configuration error."
        super().__init__(self.message)

class APIError(TTLAMaCLIException):
    """Raised when there is an error with the API request."""
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "API request error."
        super().__init__(self.message)
