"""Commands for TTL-LAMa CLI.

.. prefix:: `ttlama auth`

.. CLI::
    - `login`: Login to TTL-LAMa.
        - `internal`: Login with an internal account.
    - `logout`: Logout from TTL-LAMa.
    - `status`: Display the current authentication status.
    - `password-chg`: Change the password for the current user.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import json
import hmac
import secrets
import time
from typing import Any, cast
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
import webbrowser

import typer
from rich.console import Console
from rich.table import Table

from ..api_client import (
    authenticate_internal,
    begin_oidc_device_authorization,
    exchange_oidc_cli_ticket,
    poll_oidc_device_authorization,
    request_api,
)
from ..config_store import load_server_config
from ..token_store import (
    delete_access_token,
    get_access_token,
    save_access_token,
)
from ..exc import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    TokenStorageError,
)
from ..objects import HTTPMethod, ServerParameters, SpecificRequest
from ..utils import json_to_yaml

INVALID_RESPONSE = "The API status response is invalid."
OIDC_CALLBACK_TIMEOUT = 300
DEVICE_POLL_INCREMENT = 5

app = typer.Typer(
    no_args_is_help=True,
    help="Authentication to a TTL-LAMa.",
)

login_app = typer.Typer(
    no_args_is_help=True,
    help="Login to TTL-LAMa.",
)

app.add_typer(login_app, name="login")


class _OidcCallbackServer(HTTPServer):
    """Receive one state-verified OIDC ticket on the loopback interface."""

    def __init__(self, state: str) -> None:
        self.expected_state = state
        self.callback_ticket: str | None = None
        self.callback_error: str | None = None
        self.callback_received = False
        super().__init__(("127.0.0.1", 0), _OidcCallbackHandler)


class _OidcCallbackHandler(BaseHTTPRequestHandler):
    """Handle the local OIDC redirect without logging its query string."""

    def do_GET(self) -> None:   # pylint: disable=C0103
        """Validate the loopback path and state, then retain only the ticket."""
        server = cast(_OidcCallbackServer, self.server)
        parsed = urlsplit(self.path)
        parameters = parse_qs(parsed.query)
        state_values = parameters.get("state", [])
        ticket_values = parameters.get("ticket", [])
        if parsed.path != "/callback":
            self.send_error(404)
            return
        if (
            len(state_values) != 1
            or not hmac.compare_digest(state_values[0], server.expected_state)
        ):
            server.callback_error = "OIDC callback state did not match."
            server.callback_received = True
            self._respond(400, "Login response rejected.")
            return
        if parameters.get("error") or len(ticket_values) != 1 or not ticket_values[0]:
            server.callback_error = "OIDC authentication was not completed."
            server.callback_received = True
            self._respond(400, "Login was not completed. Return to the CLI.")
            return

        server.callback_ticket = ticket_values[0]
        server.callback_received = True
        self._respond(200, "Authentication complete. You may close this window.")

    def log_message(self, *args: Any) -> None:  # type: ignore[override]
        """Do not log callback URLs, which contain the temporary ticket."""

    def _respond(self, http_status: int, message: str) -> None:
        body = message.encode("utf-8")
        self.send_response(http_status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)


def _browser_oidc_login(server: ServerParameters) -> str:
    """Complete OIDC login through a local callback and one-time ticket."""
    state = secrets.token_urlsafe(32)
    with _OidcCallbackServer(state) as callback_server:
        callback_server.timeout = 0.25
        callback_url = f"http://127.0.0.1:{callback_server.server_port}/callback"
        login_url = (
            f"{server.server_url}:{server.server_port}/auth/login?"
            + urlencode({"cli_callback_url": callback_url, "cli_state": state})
        )
        try:
            opened = webbrowser.open(login_url)
        except webbrowser.Error:
            opened = False
        if not opened:
            typer.echo(f"Open this URL to sign in: {login_url}")

        deadline = time.monotonic() + OIDC_CALLBACK_TIMEOUT
        while not callback_server.callback_received and time.monotonic() < deadline:
            callback_server.handle_request()

        callback_ticket = callback_server.callback_ticket
        callback_error = callback_server.callback_error
        callback_received = callback_server.callback_received
    if not callback_received:
        raise APIError("Timed out waiting for the OIDC browser callback.")
    if callback_error is not None or callback_ticket is None:
        raise AuthenticationError(callback_error or "OIDC authentication failed.")
    return exchange_oidc_cli_ticket(server, callback_ticket)


def _device_authorization_details(
    response: dict[str, object],
) -> tuple[str, str, str, int, int]:
    """Validate and unpack the public fields of a device authorization response."""
    device_code = response.get("device_code")
    user_code = response.get("user_code")
    verification_uri = response.get(
        "verification_uri_complete",
        response.get("verification_uri"),
    )
    expires_in = response.get("expires_in")
    interval = response.get("interval", 5)
    if (
        not isinstance(device_code, str)
        or not device_code
        or not isinstance(user_code, str)
        or not user_code
        or not isinstance(verification_uri, str)
        or not verification_uri
        or not isinstance(expires_in, int)
        or expires_in <= 0
        or not isinstance(interval, int)
        or interval <= 0
    ):
        raise APIError("OIDC device authorization response is invalid.")
    return device_code, user_code, verification_uri, expires_in, interval


def _poll_distant_oidc_login(
    server: ServerParameters,
    device_code: str,
    expires_in: int,
    interval: int,
) -> str:
    """Poll until authorization succeeds, is denied, or expires."""
    deadline = time.monotonic() + expires_in
    while time.monotonic() < deadline:
        time.sleep(interval)
        result = poll_oidc_device_authorization(server, device_code)
        status_value = result.get("status")
        if status_value == "complete":
            token = result.get("access_token")
            if isinstance(token, str) and token:
                return token
            raise APIError("OIDC API response does not contain a valid access token.")
        if status_value == "pending":
            continue
        if status_value == "slow_down":
            interval += DEVICE_POLL_INCREMENT
            continue
        if status_value == "denied":
            raise AuthenticationError("OIDC device authorization was denied.")
        if status_value == "expired":
            raise AuthenticationError("OIDC device authorization expired.")
        raise APIError("OIDC device authorization response is invalid.")
    raise AuthenticationError("OIDC device authorization expired.")


def _distant_oidc_login(server: ServerParameters) -> str:
    """Complete OIDC login by polling the server-side device authorization relay."""
    response = begin_oidc_device_authorization(server)
    device_code, user_code, verification_uri, expires_in, interval = (
        _device_authorization_details(response)
    )
    typer.echo(f"Open {verification_uri} and enter code {user_code}.")
    return _poll_distant_oidc_login(server, device_code, expires_in, interval)


def _status_payload(response: object) -> dict[str, object]:
    """Validate and restrict the identity and session data returned by the API."""
    if not isinstance(response, dict):
        raise APIError(INVALID_RESPONSE)
    response_data = cast(dict[str, object], response)
    raw_user = response_data.get("user")
    raw_sessions = response_data.get("sessions")
    if not isinstance(raw_user, dict) or not isinstance(raw_sessions, list):
        raise APIError(INVALID_RESPONSE)

    user_data = cast(dict[str, object], raw_user)
    user = {
        key: user_data.get(key)
        for key in ("id", "username", "email", "is_admin")
    }
    sessions: list[dict[str, str]] = []
    for raw_session in cast(list[object], raw_sessions):
        if not isinstance(raw_session, dict):
            raise APIError(INVALID_RESPONSE)
        session_data = cast(dict[str, object], raw_session)
        expiration = session_data.get("expires_at")
        if not isinstance(expiration, str):
            raise APIError(INVALID_RESPONSE)
        sessions.append({"expires_at": expiration})

    return {
        "session": "active" if sessions else "inactive",
        "user": user,
        "sessions": sessions,
    }


def _display_status(
    status_data: dict[str, object],
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """Display status as JSON, YAML, or a Rich table."""
    if json_output:
        typer.echo(json.dumps(status_data, ensure_ascii=False, indent=2))
        return
    if yaml_output:
        typer.echo(json_to_yaml(json.dumps(status_data, ensure_ascii=False)))
        return

    typer.echo()
    table = Table(title="Authentication Status", expand=True)
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Session", str(status_data["session"]))
    user = cast(dict[str, object] | None, status_data["user"])
    if user is not None:
        table.add_row("User", str(user["username"] or "-"))
        table.add_row("Email", str(user["email"] or "-"))
        table.add_row("Administrator", "yes" if user["is_admin"] else "no")
    sessions = cast(list[dict[str, str]], status_data["sessions"])
    table.add_row("Active sessions", str(len(sessions)))
    for index, session in enumerate(sessions, start=1):
        table.add_row(f"Expiration {index}", session["expires_at"])
    Console().print(table)


@login_app.command("internal")
def login_internal(
    user: str = typer.Option(
        ...,
        "--user",
        help="Username for internal login.",
    ),
) -> None:
    """Connect with an internal account to a TTL-LAMa session."""
    try:
        server_url, server_port = load_server_config()
        token = authenticate_internal(
            server_url,
            server_port,
            user,
            typer.prompt("Password", hide_input=True),
        )
        save_access_token(
            server_url,
            server_port,
            token,
        )
    except (APIError, AuthenticationError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Login successful. Token saved in the system keyring.")


@login_app.command("oidc")
def login_oidc(
    distant: bool = typer.Option(
        False,
        "--distant",
        help="Use a device code for sign-in from another browser or device.",
    ),
) -> None:
    """Sign in with the configured OIDC provider."""
    try:
        server_url, server_port = load_server_config()
        server = ServerParameters(server_url=server_url, server_port=server_port)
        token = _distant_oidc_login(server) if distant else _browser_oidc_login(server)
        save_access_token(server_url, server_port, token)
    except (
        APIError,
        AuthenticationError,
        AuthorizationError,
        TokenStorageError,
    ) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        typer.echo("OIDC login cancelled.", err=True)
        raise typer.Exit(code=1) from None

    typer.echo("OIDC login successful. Token saved in the system keyring.")


@app.command("logout")
def logout() -> None:
    """Revoke the current session and remove its local token."""
    try:
        server_url, server_port = load_server_config()
        token = get_access_token(server_url, server_port)
    except (FileNotFoundError, ValueError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    if not token:
        typer.echo("No active session. Already logged out.")
        return

    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                endpoint="auth/logout",
                method=HTTPMethod.POST,
            ),
        )
    except AuthenticationError:
        try:
            delete_access_token(server_url, server_port)
        except TokenStorageError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from None
        typer.echo("The session was already inactive. Local token deleted.")
        return
    except (APIError, AuthorizationError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    try:
        delete_access_token(server_url, server_port)
    except TokenStorageError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None
    typer.echo("Logout successful. Local token deleted.")


@app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Output status as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output status as YAML."),
    check_connected: bool = typer.Option(
        False,
        "--check",
        help="Exit with status 1 when no active session is available.",
    ),
) -> None:
    """Display the current identity and active session expirations."""
    if json_output and yaml_output:
        typer.echo("Choose only one output option: --json or --yaml.", err=True)
        raise typer.Exit(code=1)

    try:
        server_url, server_port = load_server_config()
        token = get_access_token(server_url, server_port)
    except (FileNotFoundError, ValueError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    status_data: dict[str, object]
    if token:
        try:
            response = request_api(
                server=ServerParameters(server_url=server_url, server_port=server_port),
                token=token,
                specific_request=SpecificRequest(
                    endpoint="users/me",
                    method=HTTPMethod.GET,
                ),
            )
            status_data = _status_payload(response)
        except AuthenticationError:
            typer.echo("Token invalid or expired. Login again.", err=True)
            raise typer.Exit(code=1) from None
        except (APIError, AuthorizationError) as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from None
    else:
        status_data = {"session": "inactive", "user": None, "sessions": []}

    _display_status(status_data, json_output=json_output, yaml_output=yaml_output)
    if check_connected and status_data["session"] != "active":
        raise typer.Exit(code=1)


@app.command("password-chg")
def change_password() -> None:
    """Change the password of the authenticated account."""
    try:
        server_url, server_port = load_server_config()
        token = get_access_token(server_url, server_port)
        if not token:
            raise TokenStorageError("No access token is stored for this instance.")

        current_password = typer.prompt("Current password", hide_input=True)
        new_password = typer.prompt("New password", hide_input=True)
        confirmation = typer.prompt("Confirm new password", hide_input=True)
        if new_password != confirmation:
            typer.echo("New passwords do not match.", err=True)
            raise typer.Exit(code=1)

        request_api(
            ServerParameters(server_url=server_url, server_port=server_port),
            token,
            SpecificRequest(
                endpoint="users/me/password",
                method=HTTPMethod.PATCH,
                json_body={
                    "current_password": current_password,
                    "new_password": new_password,
                },
            ),
        )
    except (FileNotFoundError, ValueError, APIError, AuthenticationError,
            AuthorizationError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Password changed. Reconnect → All sessions are revoked.")
