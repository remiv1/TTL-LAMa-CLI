"""User management commands for the TTL-LAMa CLI.

.. CLI:: `ttlama admin **users**`
    - `list`: list all users.
        - `--device`: filter users by device ID.
        - `--lease`: filter users by lease ID.
        - `--profile`: filter users by profile ID.
        - `--json`: output the list of users in JSON format.
        - `--yaml`: output the list of users in YAML format.
    - `get`: retrieve a specific user by ID.
        - `--json`: output the user data in JSON format.
        - `--yaml`: output the user data in YAML format.
    - `create`: create a new user.
        - `--file`: path to a JSON or YAML file containing the user data.
    - `update`: update an existing user.
        - `--user`: ID of the user to update.
        - `--file`: path to a JSON or YAML file containing the user data.
    - `delete`: delete a user.
        - `--user`: ID of the user to delete.
    - `assign`: assign a profile to a user.
        - `--user`: ID of the user.
        - `--profile`: ID of the profile.
    - `unassign`: revoke a user's profile assignment.
        - `--user`: ID of the user.
        - `--profile`: ID of the profile.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from .. import (
    display_structured_output,
    get_server_and_token as _get_server_and_token,
    load_data_file as _load_data_file,
    validate_output_options,
)
from ...api_client import request_api
from ...objects import HTTPMethod, SpecificRequest, ServerParameters
from ...objects.requests import JSONValue
from ...exc import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    handle_api_error,
)
from ...utils import json_to_yaml

users_app = typer.Typer(
    no_args_is_help=True,
    help="User management commands for the TTL-LAMa CLI.",
)

EDITABLE_USER_FIELDS = {"username", "email", "enabled", "is_admin"}


def _load_user_file(file_path: Path) -> dict[str, JSONValue]:
    """Load a user request body from a JSON or YAML file.

    :param file_path: Path to the JSON or YAML user data file.
    :type file_path: Path
    :returns: Dictionary representing the user request body.
    :rtype: dict[str, JSONValue]
    """
    return _load_data_file(file_path, "user")


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
        help="Output the list of users in JSON format."
    ),
    yaml_output: bool = typer.Option(
        False,
        "--yaml",
        help="Output the list of users in YAML format."
    ),
) -> None:
    """Manage users in the TTL-LAMa CLI.

    :param device: Filter by device ID.
    :type device: int | None
    :param lease: Filter by lease ID.
    :type lease: int | None
    :param profile: Filter by profile ID.
    :type profile: int | None
    :param json_output: Whether to output the list of users in JSON format.
    :type json_output: bool
    :param yaml_output: Whether to output the list of users in YAML format.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)
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
        if not isinstance(users, list):
            typer.echo("The API response isn't a user list.")
            raise typer.Exit(code=1)
    except (AuthorizationError, AuthenticationError, APIError) as e:
        handle_api_error(e)

    user_rows = cast(list[dict[str, object]], users)
    if display_structured_output(
        user_rows,
        json_output=json_output,
        yaml_output=yaml_output,
        yaml_root="users",
    ):
        return

    typer.echo()
    table = Table(title="Users", expand=True)
    table.add_column("User ID", justify="left", style="cyan", no_wrap=True, overflow="ellipsis")
    table.add_column("Username", style="green", overflow="ellipsis")
    table.add_column("Active", justify="center", style="red", overflow="ellipsis")
    table.add_column("Admin", justify="center", style="red", overflow="ellipsis")
    for u in user_rows:
        table.add_row(
            str(u.get("id", "")),
            str(u.get("username", "")),
            str(u.get("enabled", "")),
            str(u.get("is_admin", "")),
        )
    console = Console()
    console.print(table)


@users_app.command("create")
def create_user(
    file_path: Path = typer.Option(
        ...,
        "--file",
        help="Path to a JSON or YAML file containing user data.",
    ),
) -> None:
    """Create a user from a JSON or YAML file.

    :param file_path: Path to a JSON or YAML file containing user data.
    :type file_path: Path
    """
    user_data = _load_user_file(file_path)
    url, port, token = _get_server_and_token()

    request = SpecificRequest(
        method=HTTPMethod.POST,
        endpoint="admin/users",
        json_body=user_data,
    )
    result: dict[str, object] | list[dict[str, object]] | None = None
    try:
        result = request_api(
            server=ServerParameters(server_url=url, server_port=port),
            token=token,
            specific_request=request,
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)

    typer.echo("User created successfully.")
    if isinstance(result, dict):
        generated_password = result.get("generated_password")
        if isinstance(generated_password, str):
            typer.echo(f"Generated password (shown only once): {generated_password}")
            typer.echo("Save it now; it cannot be retrieved later.")


@users_app.command("update")
def update_user(
    user_id: str = typer.Option(
        ...,
        "--user",
        help="Specify the ID of the user to update.",
    ),
    file_path: Path = typer.Option(
        ...,
        "--file",
        help="Path to a JSON or YAML file containing fields to update.",
    ),
) -> None:
    """Update a user from a JSON or YAML file.

    :param user_id: The ID of the user to update.
    :type user_id: str
    :param file_path: Path to a JSON or YAML file containing fields to update.
    :type file_path: Path
    """
    user_data = _load_user_file(file_path)
    url, port, token = _get_server_and_token()

    request = SpecificRequest(
        method=HTTPMethod.PATCH,
        endpoint=f"admin/users/{user_id}",
        json_body=user_data,
    )
    try:
        request_api(
            server=ServerParameters(server_url=url, server_port=port),
            token=token,
            specific_request=request,
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)

    typer.echo(f"User {user_id} updated successfully.")


@users_app.command("delete")
def delete_user(
    user_id: str = typer.Option(
        ...,
        "--user",
        help="Specify the ID of the user to delete.",
    ),
) -> None:
    """Delete a user by ID.

    :param user_id: The ID of the user to delete.
    :type user_id: str

    .. note::
        This is a logical deletion; the user will be marked as deleted but not permanently
        removed from the database. Until then, the user record will remain in the system.
    """
    url, port, token = _get_server_and_token()

    request = SpecificRequest(
        method=HTTPMethod.DELETE,
        endpoint=f"admin/users/{user_id}",
    )
    try:
        request_api(
            server=ServerParameters(server_url=url, server_port=port),
            token=token,
            specific_request=request,
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)

    typer.echo(f"User {user_id} deleted successfully.")


@users_app.command("assign")
def assign_profile(
    user_id: str = typer.Option(
        ...,
        "--user",
        help="Specify the ID of the user to assign the profile to.",
    ),
    profile_id: int = typer.Option(
        ...,
        "--profile",
        help="Specify the ID of the profile to assign.",
    ),
) -> None:
    """Assign a profile to a user.

    :param user_id: The ID of the user to assign the profile to.
    :type user_id: str
    :param profile_id: The ID of the profile to assign.
    :type profile_id: int
    """
    url, port, token = _get_server_and_token()
    request = SpecificRequest(
        method=HTTPMethod.PUT,
        endpoint=f"admin/users/{user_id}/profiles/{profile_id}",
    )
    try:
        request_api(
            server=ServerParameters(server_url=url, server_port=port),
            token=token,
            specific_request=request,
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)

    typer.echo(f"Profile {profile_id} assigned to user {user_id} successfully.")


@users_app.command("unassign")
def unassign_profile(
    user_id: str = typer.Option(
        ...,
        "--user",
        help="Specify the ID of the user to unassign the profile from.",
    ),
    profile_id: int = typer.Option(
        ...,
        "--profile",
        help="Specify the ID of the profile to unassign.",
    ),
) -> None:
    """Revoke a profile assignment from a user.

    :param user_id: The ID of the user to unassign the profile from.
    :type user_id: str
    :param profile_id: The ID of the profile to unassign.
    :type profile_id: int
    """
    url, port, token = _get_server_and_token()
    request = SpecificRequest(
        method=HTTPMethod.DELETE,
        endpoint=f"admin/users/{user_id}/profiles/{profile_id}",
    )
    try:
        request_api(
            server=ServerParameters(server_url=url, server_port=port),
            token=token,
            specific_request=request,
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)

    typer.echo(f"Profile {profile_id} unassigned from user {user_id} successfully.")


@users_app.command("get")
def get_user(
    user_id: str = typer.Argument(
        ...,
        help="Specify the ID of the user to retrieve."
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output the user information in JSON format."
    ),
    yaml_output: bool = typer.Option(
        False,
        "--yaml",
        help="Output the user information in YAML format."
    ),
) -> None:
    """Get a specific user in the TTL-LAMa CLI.

    :param user_id: The ID of the user to retrieve.
    :type user_id: str
    :param json_output: Whether to output the user information in JSON format.
    :type json_output: bool
    :param yaml_output: Whether to output the user information in YAML format.
    :type yaml_output: bool
    """
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
        user = result
        if not user:
            typer.echo(f"User with ID {user_id} not found.")
            raise typer.Exit(code=1)
    except (AuthorizationError, AuthenticationError, APIError) as e:
        handle_api_error(e)

    if user is None:
        typer.echo(f"User with ID {user_id} could not be retrieved.")
        raise typer.Exit(code=1)

    editable_user = {
        key: value
        for key, value in user.items()
        if key in EDITABLE_USER_FIELDS
    }

    if json_output:
        typer.echo(json.dumps(editable_user, ensure_ascii=False, indent=4))
        raise typer.Exit()
    if yaml_output:
        typer.echo(json_to_yaml(json.dumps(editable_user, ensure_ascii=False, indent=4)))
        raise typer.Exit()
    typer.echo()
    table = Table(title=f"User {user.get('username', '')} Details", expand=True)
    table.add_column("Field", style="cyan", no_wrap=True, overflow="ellipsis")
    table.add_column("Value", style="green", overflow="ellipsis")
    for key, value in user.items():
        table.add_row(str(key), str(value))
    console = Console()
    console.print(table)
