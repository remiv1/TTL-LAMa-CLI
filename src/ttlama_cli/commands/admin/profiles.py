"""Profile management commands for the TTL-LAMa CLI.

.. CLI:: ``ttlama admin profiles``
    - ``list``: list profiles with optional relationship filters.
    - ``get``: retrieve a profile.
    - ``create``: create a profile from a JSON or YAML file.
    - ``update``: update a profile from a JSON or YAML file.
    - ``delete``: revoke a profile.

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
    display_profiles as _display_profiles,
    get_server_and_token as _get_server_and_token,
    load_data_file as _load_data_file,
    profile_rows as _profile_rows,
    validate_output_options,
)
from ...api_client import request_api
from ...exc import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    handle_api_error,
)
from ...objects import HTTPMethod, ServerParameters, SpecificRequest
from ...objects.requests import JSONValue
from ...utils import json_to_yaml

profiles_app = typer.Typer(
    no_args_is_help=True,
    help="Profile management commands for the TTL-LAMa CLI.",
)


def _load_profile_file(file_path: Path) -> dict[str, JSONValue]:
    """Load a profile request body from a JSON or YAML file.

    :param file_path: The path to the JSON or YAML file containing the profile data.
    :type file_path: Path
    :returns: The loaded profile data as a dictionary.
    :rtype: dict[str, JSONValue]
    """
    return _load_data_file(file_path, "profile")


def _create_filters(
    user: str | None = None,
    device: int | None = None,
    lease: int | None = None,
) -> dict[str, str | int] | None:
    """Create combined profile relationship filters.

    :param user: Filter by assigned user UUID.
    :type user: str | None
    :param device: Filter by device ID.
    :type device: int | None
    :param lease: Filter by lease ID.
    :type lease: int | None
    :returns: A dictionary of filters or None if no filters are set.
    :rtype: dict[str, str | int] | None
    """
    filters = {
        key: value
        for key, value in {"user": user, "device": device, "lease": lease}.items()
        if value is not None
    }
    return filters or None


def _profile_update_data(response: object) -> dict[str, JSONValue]:
    """Flatten a profile response into fields accepted by the update API.

    :param response: The profile response object from the API.
    :type response: object
    :returns: A dictionary of fields suitable for the update API.
    :rtype: dict[str, JSONValue]
    """
    if not isinstance(response, dict):
        raise APIError("The API response isn't a profile.")
    profile = cast(dict[str, object], response)
    name = profile.get("name")
    if not isinstance(name, str):
        raise APIError("The API profile response has no valid name.")

    update_data: dict[str, JSONValue] = {"name": name}
    raw_policy = profile.get("policy")
    if raw_policy is None:
        return update_data
    if not isinstance(raw_policy, dict):
        raise APIError("The API profile policy is invalid.")

    policy = cast(dict[str, object], raw_policy)
    default_duration = policy.get("default_duration")
    maximum_duration = policy.get("maximum_duration")
    networks = policy.get("networks")
    if (
        not isinstance(default_duration, str)
        or not isinstance(maximum_duration, str)
        or not isinstance(networks, list)
        or any(
            not isinstance(network, str)
            for network in cast(list[object], networks)
        )
    ):
        raise APIError("The API profile policy is incomplete or invalid.")

    update_data.update(
        default_duration=default_duration,
        maximum_duration=maximum_duration,
        networks=cast(JSONValue, cast(list[str], networks)),
    )
    return update_data


@profiles_app.command("list")
def list_profiles(
    user: str | None = typer.Option(None, "--user", help="Filter by assigned user UUID."),
    device: int | None = typer.Option(None, "--device", help="Filter by device ID."),
    lease: int | None = typer.Option(None, "--lease", help="Filter by lease ID."),
    json_output: bool = typer.Option(False, "--json", help="Output profiles as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output profiles as YAML."),
) -> None:
    """List profiles, optionally filtered by user, device, or lease.

    :param user: Filter by assigned user UUID.
    :type user: str | None
    :param device: Filter by device ID.
    :type device: int | None
    :param lease: Filter by lease ID.
    :type lease: int | None
    :param json_output: Whether to output the profiles as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output the profiles as YAML.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)

    server_url, server_port, token = _get_server_and_token()
    try:
        response = request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.GET,
                endpoint="admin/profiles",
                params=_create_filters(user=user, device=device, lease=lease),
            ),
        )
        profiles = _profile_rows(response)
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if not profiles:
        typer.echo("No profiles found.")
        raise typer.Exit(code=1)
    _display_profiles(profiles, json_output=json_output, yaml_output=yaml_output)


@profiles_app.command("get")
def get_profile(
    profile_id: int = typer.Option(..., "--profile", help="Profile ID to retrieve."),
    json_output: bool = typer.Option(False, "--json", help="Output the profile as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output the profile as YAML."),
) -> None:
    """Retrieve a profile and display its updateable fields.

    :param profile_id: The ID of the profile to retrieve.
    :type profile_id: int
    :param json_output: Whether to output the profile as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output the profile as YAML.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)

    server_url, server_port, token = _get_server_and_token()
    try:
        response = request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.GET,
                endpoint=f"admin/profiles/{profile_id}",
            ),
        )
        update_data = _profile_update_data(response)
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if json_output:
        typer.echo(json.dumps(update_data, ensure_ascii=False, indent=4))
        return
    if yaml_output:
        typer.echo(json_to_yaml(json.dumps(update_data, ensure_ascii=False, indent=4)))
        return

    table = Table(title=f"Profile {profile_id}", expand=True)
    table.add_column("Field", style="cyan", overflow="ellipsis")
    table.add_column("Value", style="green", overflow="ellipsis")
    for key, value in update_data.items():
        table.add_row(
            key,
            json.dumps(value, ensure_ascii=False)
                if isinstance(value, list)
                else str(value),
        )
    Console().print(table)


@profiles_app.command("create")
def create_profile(
    file_path: Path = typer.Option(..., "--file", help="JSON or YAML profile data file."),
) -> None:
    """Create a profile from a JSON or YAML file.

    :param file_path: Path to the JSON or YAML profile data file.
    :type file_path: Path
    """
    profile_data = _load_profile_file(file_path)
    server_url, server_port, token = _get_server_and_token()
    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.POST,
                endpoint="admin/profiles",
                json_body=profile_data,
            ),
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo("Profile created successfully.")


@profiles_app.command("update")
def update_profile(
    profile_id: int = typer.Option(..., "--profile", help="Profile ID to update."),
    file_path: Path = typer.Option(..., "--file", help="JSON or YAML fields to update."),
) -> None:
    """Update a profile from a JSON or YAML file.

    :param profile_id: The ID of the profile to update.
    :type profile_id: int
    :param file_path: Path to the JSON or YAML fields to update.
    :type file_path: Path
    """
    profile_data = _load_profile_file(file_path)
    server_url, server_port, token = _get_server_and_token()
    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.PATCH,
                endpoint=f"admin/profiles/{profile_id}",
                json_body=profile_data,
            ),
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Profile {profile_id} updated successfully.")


@profiles_app.command("delete")
def delete_profile(
    profile_id: int = typer.Option(..., "--profile", help="Profile ID to revoke."),
) -> None:
    """Revoke a profile and its dependent access.

    :param profile_id: The ID of the profile to revoke.
    :type profile_id: int
    """
    server_url, server_port, token = _get_server_and_token()
    try:
        profile = request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.GET,
                endpoint=f"admin/profiles/{profile_id}",
            ),
        )
        if not isinstance(profile, dict):
            raise APIError("The API response isn't a profile.")
        profile_name = profile.get("name")
        if not isinstance(profile_name, str):
            raise APIError("The API profile response has no valid name.")
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    confirmation = typer.prompt(
        f"Type the full profile name to confirm revocation of '{profile_name}'"
    )
    if confirmation != profile_name:
        typer.echo("Profile name did not match; profile was not revoked.", err=True)
        raise typer.Exit(code=1)

    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.DELETE,
                endpoint=f"admin/profiles/{profile_id}",
            ),
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Profile {profile_id} revoked successfully.")
