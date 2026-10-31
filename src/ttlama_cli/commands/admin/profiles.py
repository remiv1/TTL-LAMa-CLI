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
from yaml import YAMLError

from ...api_client import request_api
from ...config_store import load_server_config
from ...exc import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    TokenStorageError,
    handle_api_error,
)
from ...objects import HTTPMethod, ServerParameters, SpecificRequest
from ...objects.requests import JSONValue
from ...token_store import get_access_token
from ...utils import json_to_yaml, yaml_to_json

profiles_app = typer.Typer(
    no_args_is_help=True,
    help="Profile management commands for the TTL-LAMa CLI.",
)


def _get_server_and_token() -> tuple[str, int, str]:
    """Retrieve the configured server and its access token."""
    try:
        server_url, server_port = load_server_config()
        token = get_access_token(server_url, server_port)
        if not token:
            raise TokenStorageError("No access token is stored for this server.")
    except (FileNotFoundError, ValueError, TokenStorageError) as error:
        typer.echo(f"Error retrieving server credentials: {error}", err=True)
        raise typer.Exit(code=1) from error
    return server_url, server_port, token


def _load_profile_file(file_path: Path) -> dict[str, JSONValue]:
    """Load a profile request body from a JSON or YAML file."""
    try:
        contents = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        typer.echo(f"Error reading profile data file '{file_path}': {error}", err=True)
        raise typer.Exit(code=1) from error

    try:
        data = json.loads(yaml_to_json(contents))
    except (TypeError, ValueError, YAMLError) as error:
        typer.echo(
            f"Error parsing profile data file '{file_path}': "
            "expected valid JSON or YAML.",
            err=True,
        )
        raise typer.Exit(code=1) from error

    if not isinstance(data, dict):
        typer.echo("Profile data file must contain an object at the top level.", err=True)
        raise typer.Exit(code=1)
    return cast(dict[str, JSONValue], data)


def _create_filters(
    user: str | None = None,
    device: int | None = None,
    lease: int | None = None,
) -> dict[str, str | int] | None:
    """Create combined profile relationship filters."""
    filters = {
        key: value
        for key, value in {"user": user, "device": device, "lease": lease}.items()
        if value is not None
    }
    return filters or None


def _profile_rows(response: object) -> list[dict[str, object]]:
    """Validate the list response returned by the profile API."""
    if not isinstance(response, list):
        raise APIError("The API response isn't a profile list.")
    rows = cast(list[object], response)
    if any(not isinstance(row, dict) for row in rows):
        raise APIError("The API response isn't a profile list.")
    return cast(list[dict[str, object]], rows)


def _profile_update_data(response: object) -> dict[str, JSONValue]:
    """Flatten a profile response into fields accepted by the update API."""
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


def _display_profiles(
    profiles: list[dict[str, object]],
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """Display profiles as JSON, YAML, or a Rich table."""
    if json_output:
        typer.echo(json.dumps(profiles, ensure_ascii=False, indent=4))
        return
    if yaml_output:
        typer.echo(json_to_yaml(json.dumps({"profiles": profiles}, ensure_ascii=False)))
        return

    table = Table(title="Profiles", expand=True)
    table.add_column("Profile ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", overflow="ellipsis")
    table.add_column("Default duration")
    table.add_column("Maximum duration")
    table.add_column("Networks")
    table.add_column("Status")
    for profile in profiles:
        policy_value = profile.get("policy")
        policy = (
            cast(dict[str, object], policy_value)
            if isinstance(policy_value, dict)
            else {}
        )
        networks_value = policy.get("networks")
        network_count = (
            len(cast(list[object], networks_value))
            if isinstance(networks_value, list)
            else 0
        )
        status = "revoked" if profile.get("revoked_at") is not None else "active"
        table.add_row(
            str(profile.get("id", "")),
            str(profile.get("name", "")),
            str(policy.get("default_duration", "-")),
            str(policy.get("maximum_duration", "-")),
            str(network_count),
            status,
        )
    Console().print(table)


@profiles_app.command("list")
def list_profiles(
    user: str | None = typer.Option(None, "--user", help="Filter by assigned user UUID."),
    device: int | None = typer.Option(None, "--device", help="Filter by device ID."),
    lease: int | None = typer.Option(None, "--lease", help="Filter by lease ID."),
    json_output: bool = typer.Option(False, "--json", help="Output profiles as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output profiles as YAML."),
) -> None:
    """List profiles, optionally filtered by user, device, or lease."""
    if json_output and yaml_output:
        typer.echo("Choose only one output option: --json or --yaml.", err=True)
        raise typer.Exit(code=1)

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
    """Retrieve a profile and display its updateable fields."""
    if json_output and yaml_output:
        typer.echo("Choose only one output option: --json or --yaml.", err=True)
        raise typer.Exit(code=1)

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
    """Create a profile from a JSON or YAML file."""
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
    """Update a profile from a JSON or YAML file."""
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
    """Revoke a profile and its dependent access."""
    server_url, server_port, token = _get_server_and_token()
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
