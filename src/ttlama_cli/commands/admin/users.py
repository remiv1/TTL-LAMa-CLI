"""User management commands for the TTL-LAMa CLI."""
from __future__ import annotations

import json
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from ...config_store import load_server_config
from ...token_store import get_access_token
from ...api_client import request_api
from ...objects import HTTPMethod, SpecificRequest, ServerParameters
from ...exc import AuthorizationError, APIError, AuthenticationError

users_app = typer.Typer(
    no_args_is_help=True,
    help="User management commands for the TTL-LAMa CLI.",
)

def _get_server_and_token() -> tuple[str, int, str]:
    """Retrieve the server URL, port, and access token.

    :return: Tuple containing server URL, server port, and access token.
    :rtype: tuple[str, int, str]
    :raises typer.Exit: If there is an error loading the server configuration or
    retrieving the access token.
    """
    try:
        url, port = load_server_config()
    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"Error loading server configuration: {e}")
        raise typer.Exit(code=1) from e

    try:
        token = get_access_token(url, port)
        if not token:
            raise ValueError("Access token is empty.")
    except Exception as e:
        typer.echo(f"Error retrieving access token: {e}")
        raise typer.Exit(code=1) from e

    return url, port, token

def _create_filters(
    device: int | None = None,
    lease: int | None = None,
    profile: int | None = None
) -> dict[str, int] | None:
    """Create a dictionary of filters for the API request.
    
    :param device: Device ID to filter by.
    :type device: int | None
    :param lease: Lease ID to filter by.
    :type lease: int | None
    :param profile: Profile ID to filter by.
    :type profile: int | None
    :return: Dictionary of filters, or None if no filters are set.
    :rtype: dict[str, int] | None
    """
    filters = {
        key: value
        for key, value in {
            "device": device,
            "lease": lease,
            "profile": profile
        }.items()
        if value is not None
    }
    return filters or None

def handle_api_error(e: Exception) -> None:
    """Handle API errors by printing an error message and exiting."""
    typer.echo(f"Error requesting API: {e}")
    raise typer.Exit(code=1) from e

@users_app.command("list")
def list_users(
    device: int | None = typer.Option(
        None,
        "--device",
        help="Specify the device to list users from."
    ),
    lease: int | None = typer.Option(
        None,
        "--lease",
        help="Specify the lease to list users from."
    ),
    profile: int | None = typer.Option(
        None,
        "--profile",
        help="Specify the profile to list users from."
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        is_flag=True,
        help="Output the list of users in JSON format."
    ),
) -> None:
    """Manage users in the TTL-LAMa CLI."""
    url, port, token = _get_server_and_token()
    filters = _create_filters(device=device, lease=lease, profile=profile)
    users = None

    request = SpecificRequest(
        method=HTTPMethod.GET,
        endpoint="admin/users",
        params=filters or None,
    )
    try:
        users = request_api(
            server=ServerParameters(server_url=url, server_port=port),
            token=token,
            specific_request=request
        )
        if not users:
            typer.echo("No users found.")
            raise typer.Exit(code=1)
    except (AuthorizationError, AuthenticationError, APIError) as e:
        handle_api_error(e)

    if json_output:
        typer.echo(json.dumps(users, ensure_ascii=False, indent=4))

    typer.echo()
    table = Table(title="Users", expand=True)
    table.add_column("User ID", justify="left", style="cyan", no_wrap=True, overflow="ellipsis")
    table.add_column("Username", style="green", overflow="ellipsis")
    table.add_column("Active", justify="center", style="red", overflow="ellipsis")
    table.add_column("Admin", justify="center", style="red", overflow="ellipsis")
    for u in users or []:
        table.add_row(
            str(u.get("id", "")),
            str(u.get("username", "")),
            str(u.get("enabled", "")),
            str(u.get("is_admin", "")),
        )
    console = Console()
    console.print(table)

@users_app.command("get")
def get_user(
    user_id: str = typer.Argument(
        ...,
        help="Specify the ID of the user to retrieve."
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        is_flag=True,
        help="Output the user information in JSON format."
    ),
) -> None:
    """Get a specific user in the TTL-LAMa CLI."""
    url, port, token = _get_server_and_token()

    request = SpecificRequest(
        method=HTTPMethod.GET,
        endpoint=f"admin/users/{user_id}",
    )
    user = None
    try:
        result = request_api(
            server=ServerParameters(server_url=url, server_port=port),
            token=token,
            specific_request=request
        )
        if not isinstance(result, dict):
            typer.echo("The API response isn't a user")
            raise typer.Exit(code=1)
        user = cast(dict[str, object], result)
        if not user:
            typer.echo(f"User with ID {user_id} not found.")
            raise typer.Exit(code=1)
    except (AuthorizationError, AuthenticationError, APIError) as e:
        handle_api_error(e)

    if json_output:
        typer.echo(json.dumps(user, ensure_ascii=False, indent=4))
        raise typer.Exit()
    if user is not None:
        typer.echo()
        table = Table(title=f"User {user.get('username', '')} Details", expand=True)
        table.add_column("Field", style="cyan", no_wrap=True, overflow="ellipsis")
        table.add_column("Value", style="green", overflow="ellipsis")
        for key, value in user.items():
            table.add_row(str(key), str(value))
        console = Console()
        console.print(table)
