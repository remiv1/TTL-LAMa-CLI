"""Exceptions for TTL-LAMa CLI.

.. classes::
    - `TTLAMaCLIException`: Base exception for TTL-LAMa CLI.
    - `AuthenticationError`: Raised when authentication fails.
    - `TokenStorageError`: Raised when storing or retrieving tokens fails.
    - `ServerConfigError`: Raised when there is an issue with the server configuration.
    - `APIError`: Raised when there is an error with the API request.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from typer import Exit, echo

class TTLAMaCLIException(Exception):
    """Base exception for TTL-LAMa CLI.
    
    .. author:: Rémi Verschuur <rverschuur@audit-io.fr>
    .. version:: 1.0.0
    """
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "An error occurred in TTL-LAMa CLI."
        super().__init__(self.message)

class AuthenticationError(TTLAMaCLIException):
    """Raised when authentication fails.
    
    .. author:: Rémi Verschuur <rverschuur@audit-io.fr>
    .. version:: 1.0.0
    """
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Authentication failed."
        super().__init__(self.message)

class AuthorizationError(TTLAMaCLIException):
    """Raised when the user does not have admin privileges.
    
    .. author:: Rémi Verschuur <rverschuur@audit-io.fr>
    .. version:: 1.0.0
    """
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "You haven't admin privileges."
        super().__init__(self.message)

class TokenStorageError(TTLAMaCLIException):
    """Raised when storing or retrieving tokens fails.
    
    .. author:: Rémi Verschuur <rverschuur@audit-io.fr>
    .. version:: 1.0.0
    """
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Token storage error."
        super().__init__(self.message)

class ServerConfigError(TTLAMaCLIException):
    """Raised when there is an issue with the server configuration.
    
    .. author:: Rémi Verschuur <rverschuur@audit-io.fr>
    .. version:: 1.0.0
    """
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Server configuration error."
        super().__init__(self.message)

class APIError(TTLAMaCLIException):
    """Raised when there is an error with the API request.
    
    .. author:: Rémi Verschuur <rverschuur@audit-io.fr>
    .. version:: 1.0.0
    """
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "API request error."
        super().__init__(self.message)

def handle_api_error(e: Exception) -> None:
    """Handle API errors by printing an error message and exiting."""
    echo(f"Error requesting API: {e}")
    raise Exit(code=1) from e
