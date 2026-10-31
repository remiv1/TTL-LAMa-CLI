"""User lease command group, reserved for lease operations.

.. prefix:: `ttlama user leases`

.. CLI::
    - `list` : List the user's leases.
    - `get` : Display details of a specific lease.
        - [--id] : Specify the lease ID.
    - `create` : Create a new lease.
        - [--file] : Specify the file containing lease details.
    - `revoke` : Revoke a specific lease.
        - [--id] : Specify the lease ID.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .. import (
    display_structured_output,
    load_data_file,
    request_configured_api,
    resource_object,
    resource_rows,
    validate_output_options,
)
from ...exc import APIError, AuthenticationError, AuthorizationError, handle_api_error
from ...objects import HTTPMethod, SpecificRequest

app = typer.Typer(
    no_args_is_help=True,
    help="Inspect leases owned by the authenticated user.",
)


def _display_leases(
    leases: list[dict[str, object]],
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """Display leases as JSON, YAML, or a Rich table.
    
    :param leases: The list of leases to display.
    :type leases: list[dict[str, object]]
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    if display_structured_output(
        leases,
        json_output=json_output,
        yaml_output=yaml_output,
        yaml_root="leases",
    ):
        return

    table = Table(title="Leases", expand=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Device ID")
    table.add_column("Profile ID")
    table.add_column("Created")
    table.add_column("Ends")
    table.add_column("Status")
    for lease in leases:
        table.add_row(
            str(lease.get("id", "")),
            str(lease.get("device_id", "")),
            str(lease.get("profile_id", "")),
            str(lease.get("created_at") or "-"),
            str(lease.get("ended_at") or "-"),
            str(lease.get("status", "")),
        )
    Console().print(table)


def _display_lease(
    lease: dict[str, object],
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """Display one lease as JSON, YAML, or a Rich table.

    :param lease: The lease to display.
    :type lease: dict[str, object]
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    if display_structured_output(
        lease,
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return

    table = Table(title=f"Lease {lease.get('id', '')}", expand=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green", overflow="ellipsis")
    for key, value in lease.items():
        table.add_row(key, str(value if value is not None else "-"))
    Console().print(table)


@app.command("list")
def list_leases(
    json_output: bool = typer.Option(False, "--json", help="Output leases as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output leases as YAML."),
) -> None:
    """List leases owned by the authenticated user.

    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)
    try:
        leases = resource_rows(
            request_configured_api(SpecificRequest(
                method=HTTPMethod.GET,
                endpoint="users/me/leases",
            )),
            "lease",
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if not leases and not (json_output or yaml_output):
        typer.echo("No leases found.")
        return
    _display_leases(leases, json_output=json_output, yaml_output=yaml_output)


@app.command("get")
def get_lease(
    lease_id: int = typer.Option(..., "--id", help="Lease ID to retrieve."),
    json_output: bool = typer.Option(False, "--json", help="Output the lease as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output the lease as YAML."),
) -> None:
    """Retrieve an owned lease by ID.

    :param lease_id: The ID of the lease to retrieve.
    :type lease_id: int
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)
    try:
        lease = resource_object(
            request_configured_api(SpecificRequest(
                method=HTTPMethod.GET,
                endpoint=f"users/me/leases/{lease_id}",
            )),
            "lease",
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    _display_lease(lease, json_output=json_output, yaml_output=yaml_output)


@app.command("create")
def create_lease(
    file_path: Path = typer.Option(..., "--file", help="JSON or YAML lease data file."),
) -> None:
    """Create a lease from a JSON or YAML file.

    :param file_path: Path to the JSON or YAML lease data file.
    :type file_path: Path
    """
    lease_data = load_data_file(file_path, "lease")
    try:
        lease = resource_object(
            request_configured_api(SpecificRequest(
                method=HTTPMethod.POST,
                endpoint="users/me/leases",
                json_body=lease_data,
            )),
            "lease",
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Lease {lease.get('id', '')} created successfully.")


@app.command("revoke")
def revoke_lease(
    lease_id: int = typer.Option(..., "--id", help="Lease ID to revoke."),
) -> None:
    """Revoke an owned lease without deleting its history.

    :param lease_id: The ID of the lease to revoke.
    :type lease_id: int
    """
    if not typer.confirm(f"Revoke lease {lease_id}?"):
        raise typer.Exit(code=1)
    try:
        request_configured_api(SpecificRequest(
            method=HTTPMethod.POST,
            endpoint=f"users/me/leases/{lease_id}/revoke",
        ))
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Lease {lease_id} revoked successfully.")
