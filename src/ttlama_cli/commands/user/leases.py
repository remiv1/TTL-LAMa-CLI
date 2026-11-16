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

import base64
import os
import subprocess
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

PROVISIONING_REQUEST_TIMEOUT_SECONDS = 60.0

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


@app.command("ls")
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


@app.command("configuration")
def get_configuration(
    lease_id: int = typer.Option(..., "--id", help="Active lease ID."),
    private_key_file: Path | None = typer.Option(
        None, "--private-key-file",
        help="Local WireGuard private key.",
    ),
    output: Path | None = typer.Option(
        None, "--output",
        help="New private configuration file to create.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output public parameters as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output public parameters as YAML."),
) -> None:
    """Retrieve public parameters or assemble a private configuration locally.

    :param lease_id: Identifier of the owned active lease.
    :param private_key_file: Local key, never sent to the server.
    :param output: New configuration path, created with owner-only permissions.
    :param json_output: Output public parameters as JSON.
    :param yaml_output: Output public parameters as YAML.
    """
    validate_output_options(json_output, yaml_output)
    if (private_key_file is None) != (output is None) or (output and (json_output or yaml_output)):
        typer.echo("Use --private-key-file with --output, without --json or --yaml.", err=True)
        raise typer.Exit(code=1)
    try:
        parameters = resource_object(request_configured_api(SpecificRequest(
            method=HTTPMethod.GET, endpoint=f"users/me/leases/{lease_id}/configuration",
        )), "configuration")
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    if output is None or private_key_file is None:
        display_structured_output(parameters, json_output=not yaml_output, yaml_output=yaml_output)
        return
    try:
        private_key = private_key_file.read_text(encoding="ascii").strip()
        if len(base64.b64decode(private_key, validate=True)) != 32:
            raise ValueError("Invalid key length")
        public_key = subprocess.run(
            ["wg", "pubkey"], input=private_key + "\n", text=True, capture_output=True, check=True,
        ).stdout.strip()
        if public_key != parameters.get("device_public_key"):
            raise ValueError("The local key does not match the device")
        template = parameters.get("configuration_template")
        if not isinstance(template, str) or template.count("REPLACE_WITH_LOCAL_PRIVATE_KEY") != 1:
            raise ValueError("Invalid configuration template")
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as configuration:
            configuration.write(template.replace("REPLACE_WITH_LOCAL_PRIVATE_KEY", private_key))
    except (OSError, ValueError, subprocess.SubprocessError):
        typer.echo(
            "Cannot export configuration: check the local key, wg availability and unused output path.", # pylint: disable=C0301
            err=True,
        )
        raise typer.Exit(code=1) from None
    typer.echo("WireGuard configuration created locally.")


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
                timeout=PROVISIONING_REQUEST_TIMEOUT_SECONDS,
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
            timeout=PROVISIONING_REQUEST_TIMEOUT_SECONDS,
        ))
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Lease {lease_id} revoked successfully.")
