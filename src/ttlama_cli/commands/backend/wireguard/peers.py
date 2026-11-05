"""Commands for inspecting WireGuard peers as TTL-LAMa leases.

.. CLI::
    - `ls` for listing WireGuard leases.
    - `get` for retrieving a WireGuard lease.
    - `apply` for applying a WireGuard lease.
    - `delete` for removing a WireGuard lease.

.. functions::
    - `list_leases`: List leases configured on WireGuard interfaces.
    - `get_lease_command`: Retrieve a lease by its public key.
    - `apply_lease_command`: Apply a lease to a WireGuard interface.
    - `delete_lease_command`: Remove a lease from a WireGuard interface.

.. constants::
    - `LEASE_INPUT_HELP`: Help text for the lease input option.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console
from rich.table import Table

from ....drivers import WireGuardDriver
from ....drivers._common import VPNLease, VPNLeaseState
from ... import (
    display_structured_output,
    load_data_file,
    validate_output_options,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Inspect WireGuard leases.",
)
LEASE_INPUT_HELP = "JSON or YAML lease data; use '-' to read standard input."


def _invalid_lease_data(message: str) -> NoReturn:
    typer.echo(f"Invalid lease data: {message}", err=True)
    raise typer.Exit(code=1)


def _load_lease(file_path: Path) -> tuple[str, VPNLease]:
    data = load_data_file(file_path, "lease")
    interface = data.get("interface")
    lease_id = data.get("lease_id")
    device_id = data.get("device_id")
    public_key = data.get("public_key")
    addresses_data = data.get("addresses")

    if not isinstance(interface, str) or not interface or interface == "all":
        _invalid_lease_data("'interface' must name one specific interface.")
    if not isinstance(lease_id, str) or not lease_id:
        _invalid_lease_data("'lease_id' must be a non-empty string.")
    if not isinstance(device_id, str) or not device_id:
        _invalid_lease_data("'device_id' must be a non-empty string.")
    if not isinstance(public_key, str) or not public_key:
        _invalid_lease_data("'public_key' must be a non-empty string.")
    if not isinstance(addresses_data, list):
        _invalid_lease_data("'addresses' must be a list of strings.")

    addresses = tuple(
        address for address in addresses_data if isinstance(address, str)
    )
    if len(addresses) != len(addresses_data):
        _invalid_lease_data("'addresses' must be a list of strings.")

    return interface, VPNLease(
        lease_id=lease_id,
        device_id=device_id,
        public_key=public_key,
        addresses=addresses,
    )


def _lease_state_data(lease: VPNLeaseState | None) -> dict[str, object] | None:
    if lease is None:
        return None
    return {
        "interface": lease.interface,
        "identity": lease.identity,
        "addresses": list(lease.addresses),
    }


def _display_lease_state(
    lease: VPNLeaseState | None,
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    if display_structured_output(
        _lease_state_data(lease),
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return
    if lease is None:
        typer.echo("No WireGuard lease found.")
        return

    table = Table(title=f"WireGuard lease {lease.identity}", expand=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green", overflow="ellipsis")
    table.add_row("interface", lease.interface)
    table.add_row("identity", lease.identity)
    table.add_row("addresses", ", ".join(lease.addresses))
    Console().print(table)


def _display_mutation_status(
    operation: str,
    interface: str,
    lease: VPNLease,
) -> None:
    status: dict[str, object] = {
        "success": True,
        "operation": operation,
        "interface": interface,
        "identity": lease.public_key,
    }
    display_structured_output(status, json_output=True, yaml_output=False)


@app.command("ls")
def list_leases(
    interface: str = typer.Option(
        "all",
        "--interface",
        help="WireGuard interface to inspect (defaults to all interfaces).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output leases as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output leases as YAML."),
) -> None:
    """List WireGuard peers as leases.

    :param interface: The WireGuard interface to inspect, or ``all``.
    :type interface: str
    :param json_output: Whether to output leases as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output leases as YAML.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)

    try:
        leases = WireGuardDriver(interface).list_leases()
    except (OSError, RuntimeError) as error:
        typer.echo(f"Error listing WireGuard leases: {error}", err=True)
        raise typer.Exit(code=1) from error

    rows: list[dict[str, object]] = []
    for lease in leases:
        rows.append({
            "interface": lease.interface,
            "identity": lease.identity,
            "addresses": list(lease.addresses),
        })
    if display_structured_output(
        rows,
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return

    if not rows:
        typer.echo("No WireGuard leases found.")
        return

    table = Table(title="WireGuard leases", expand=True)
    table.add_column("Interface", style="cyan", no_wrap=True)
    table.add_column("Identity")
    table.add_column("Addresses")
    for lease in leases:
        table.add_row(
            lease.interface,
            lease.identity,
            ", ".join(lease.addresses),
        )
    Console().print(table)


@app.command("get")
def get_lease_command(
    file_path: Path = typer.Option(
        ...,
        "--lease",
        help=LEASE_INPUT_HELP,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output the lease as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output the lease as YAML."),
    check: bool = typer.Option(
        False,
        "--check",
        help="Exit with status 1 when the lease is not found.",
    ),
) -> None:
    """Retrieve a WireGuard lease using its full input document.

    :param file_path: JSON or YAML lease data path, or ``-`` for standard input.
    :type file_path: Path
    :param json_output: Whether to output the lease as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output the lease as YAML.
    :type yaml_output: bool
    :param check: Whether to return a non-zero status when the lease is absent.
    :type check: bool
    """
    validate_output_options(json_output, yaml_output)
    interface, lease = _load_lease(file_path)
    try:
        state = WireGuardDriver(interface).get_lease(lease.public_key, interface)
    except (OSError, RuntimeError, ValueError) as error:
        typer.echo(f"Error retrieving WireGuard lease: {error}", err=True)
        raise typer.Exit(code=1) from error

    _display_lease_state(
        state,
        json_output=json_output,
        yaml_output=yaml_output,
    )
    if state is None and check:
        raise typer.Exit(code=1)


@app.command("apply")
def apply_lease_command(
    file_path: Path = typer.Option(
        ...,
        "--lease",
        help=LEASE_INPUT_HELP,
    ),
) -> None:
    """Apply a WireGuard lease from a JSON or YAML document.

    :param file_path: JSON or YAML lease data path, or ``-`` for standard input.
    :type file_path: Path
    """
    interface, lease = _load_lease(file_path)
    try:
        result = WireGuardDriver(interface).apply_lease(lease)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "WireGuard apply operation failed.")
    except (OSError, RuntimeError, ValueError) as error:
        typer.echo(f"Error applying WireGuard lease: {error}", err=True)
        raise typer.Exit(code=1) from error
    _display_mutation_status("apply", interface, lease)


@app.command("delete")
def delete_lease_command(
    file_path: Path = typer.Option(
        ...,
        "--lease",
        help=LEASE_INPUT_HELP,
    ),
) -> None:
    """Remove a WireGuard lease using its full input document.

    :param file_path: JSON or YAML lease data path, or ``-`` for standard input.
    :type file_path: Path
    """
    interface, lease = _load_lease(file_path)
    try:
        result = WireGuardDriver(interface).revoke_lease(lease)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "WireGuard delete operation failed.")
    except (OSError, RuntimeError, ValueError) as error:
        typer.echo(f"Error deleting WireGuard lease: {error}", err=True)
        raise typer.Exit(code=1) from error
    _display_mutation_status("delete", interface, lease)
