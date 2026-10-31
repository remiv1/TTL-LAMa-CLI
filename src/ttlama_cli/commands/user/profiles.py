"""List and inspect profiles assigned to the authenticated user.

.. prefix:: `ttlama user profiles`

.. CLI::
    - `list` : List the user's profiles.
    - `get` : Display details of a specific profile.
        - [--id] : Specify the profile ID.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import typer

from .. import (
    display_profiles,
    display_structured_output,
    get_server_and_token,
    profile_rows,
    request_user_overview,
    validate_output_options,
)
from ...exc import APIError, AuthenticationError, AuthorizationError, handle_api_error

app = typer.Typer(
    no_args_is_help=True,
    help="Inspect profiles assigned to the authenticated user.",
)


def _get_profiles() -> list[dict[str, object]]:
    """Retrieve the profiles in the authenticated user's overview."""
    server_url, server_port, token = get_server_and_token()
    overview = request_user_overview(server_url, server_port, token)
    return profile_rows(overview["profiles"])


@app.command("list")
def list_profiles(
    json_output: bool = typer.Option(False, "--json", help="Output profiles as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output profiles as YAML."),
) -> None:
    """List profiles actively assigned to the current user."""
    validate_output_options(json_output, yaml_output)
    try:
        profiles = _get_profiles()
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if not profiles:
        typer.echo("No profiles assigned.")
        return
    display_profiles(profiles, json_output=json_output, yaml_output=yaml_output)


@app.command("get")
def get_profile(
    profile_id: int = typer.Option(..., "--id", help="Profile ID to retrieve."),
    json_output: bool = typer.Option(False, "--json", help="Output the profile as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output the profile as YAML."),
) -> None:
    """Retrieve an assigned profile by ID."""
    validate_output_options(json_output, yaml_output)
    try:
        profiles = _get_profiles()
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    profile = next((row for row in profiles if row.get("id") == profile_id), None)
    if profile is None:
        typer.echo(f"Profile {profile_id} is not assigned to this user.", err=True)
        raise typer.Exit(code=1)

    if display_structured_output(
        profile,
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return
    display_profiles([profile], json_output=False, yaml_output=False)
