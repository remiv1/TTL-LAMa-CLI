"""Shared helpers for CLI command groups."""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import typer
from rich.console import Console
from rich.table import Table
from yaml import YAMLError

from ..api_client import request_api
from ..config_store import load_server_config
from ..exc import APIError, TokenStorageError
from ..objects import HTTPMethod, ServerParameters, SpecificRequest
from ..objects.requests import JSONValue
from ..token_store import get_access_token
from ..utils import json_to_yaml, yaml_to_json


def get_server_and_token() -> tuple[str, int, str]:
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


def validate_output_options(json_output: bool, yaml_output: bool) -> None:
    """Reject simultaneous JSON and YAML output options."""
    if json_output and yaml_output:
        typer.echo("Choose only one output option: --json or --yaml.", err=True)
        raise typer.Exit(code=1)


def display_structured_output(
	data: dict[str, object] | list[dict[str, object]],
	*,
	json_output: bool,
	yaml_output: bool,
	yaml_root: str | None = None,
) -> bool:
    """Display JSON or YAML data and report whether a format was selected."""
    if json_output:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=4))
        return True
    if yaml_output:
        yaml_data: object = {yaml_root: data} if yaml_root is not None else data
        typer.echo(json_to_yaml(json.dumps(yaml_data, ensure_ascii=False)))
        return True
    return False


def request_configured_api(
    specific_request: SpecificRequest,
) -> dict[str, object] | list[dict[str, object]] | None:
    """Send a request with the configured server and stored access token.

    :param specific_request: The specific API request to send.
    :type specific_request: SpecificRequest
    :returns: The API response as a dictionary or a list of dictionaries.
    :rtype: dict[str, object] | list[dict[str, object]] | None
    """
    server_url, server_port, token = get_server_and_token()
    return request_api(
        server=ServerParameters(server_url=server_url, server_port=server_port),
        token=token,
        specific_request=specific_request,
    )


def load_data_file(file_path: Path, resource_name: str) -> dict[str, JSONValue]:
    """Load a JSON or YAML object from a UTF-8 request file.

    :param file_path: The path to the request file.
    :type file_path: Path
    :param resource_name: The name of the resource being loaded (for error messages).
    :type resource_name: str
    :returns: The parsed JSON or YAML object as a dictionary.
    :rtype: dict[str, JSONValue]
    """
    try:
        contents = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        typer.echo(
            f"Error reading {resource_name} data file '{file_path}': {error}",
            err=True,
        )
        raise typer.Exit(code=1) from error

    try:
        data = json.loads(yaml_to_json(contents))
    except (TypeError, ValueError, YAMLError) as error:
        typer.echo(
            f"Error parsing {resource_name} data file: expected valid JSON or YAML.",
            err=True,
        )
        raise typer.Exit(code=1) from error

    if not isinstance(data, dict):
        typer.echo(
            f"{resource_name.capitalize()} data file must contain an object "
            "at the top level.",
            err=True,
        )
        raise typer.Exit(code=1)
    return cast(dict[str, JSONValue], data)


def request_user_overview(
	server_url: str,
	server_port: int,
	token: str,
) -> dict[str, object]:
    """Fetch and validate the authenticated user's overview response.

    :param server_url: The URL of the server.
    :type server_url: str
    :param server_port: The port of the server.
    :type server_port: int
    :param token: The authentication token.
    :type token: str
    :returns: The user's overview as a dictionary.
    :rtype: dict[str, object]
    """
    response = request_api(
        server=ServerParameters(server_url=server_url, server_port=server_port),
        token=token,
        specific_request=SpecificRequest(
            method=HTTPMethod.GET,
            endpoint="users/me/overview",
        ),
    )
    if not isinstance(response, dict):
        raise APIError("The API response isn't a user overview.")
    overview = response
    if not isinstance(overview.get("user"), dict):
        raise APIError("The API response has no valid user identity.")
    for key in ("devices", "leases", "profiles"):
        rows = overview.get(key)
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) for row in cast(list[object], rows)
        ):
            raise APIError(f"The API response has no valid {key} list.")
    return overview


def profile_rows(response: object) -> list[dict[str, object]]:
    """Validate the list response returned by a profile endpoint.

    :param response: The API response to validate.
    :type response: object
    :returns: A list of profile objects.
    :rtype: list[dict[str, object]]
    """
    return resource_rows(response, "profile")


def resource_rows(response: object, resource_name: str) -> list[dict[str, object]]:
    """Validate an API list response containing object rows.

    :param response: The API response to validate.
    :type response: object
    :param resource_name: The name of the resource being validated.
    :type resource_name: str
    :returns: A list of resource objects.
    :rtype: list[dict[str, object]]
    """
    if not isinstance(response, list):
        raise APIError(f"The API response isn't a {resource_name} list.")
    rows = cast(list[object], response)
    if any(not isinstance(row, dict) for row in rows):
        raise APIError(f"The API response isn't a {resource_name} list.")
    return cast(list[dict[str, object]], rows)


def resource_object(response: object, resource_name: str) -> dict[str, object]:
    """Validate an API response containing one object.

    :param response: The API response to validate.
    :type response: object
    :param resource_name: The name of the resource being validated.
    :type resource_name: str
    :returns: The resource object.
    :rtype: dict[str, object]
    """
    if not isinstance(response, dict):
        raise APIError(f"The API response isn't a {resource_name}.")
    return cast(dict[str, object], response)


def display_profiles(
	profiles: list[dict[str, object]],
	*,
	json_output: bool,
	yaml_output: bool,
) -> None:
    """Display profiles as JSON, YAML, or a Rich table.

    :param profiles: The list of profiles to display.
    :type profiles: list[dict[str, object]]
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    if display_structured_output(
        profiles,
        json_output=json_output,
        yaml_output=yaml_output,
        yaml_root="profiles",
    ):
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
