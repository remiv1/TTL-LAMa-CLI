"""User device command group, reserved for device operations.

.. prefix:: `ttlama user devices`

.. CLI::
    - `list` : List the user's devices.
    - `get` : Display details of a specific device.
        - [--id] : Specify the device ID.
    - `add` : Add a new device.
        - [--file] : Specify the file containing device details.
    - `delete` : Remove a specific device.
        - [--id] : Specify the device ID.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0"""
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
    help="Inspect devices owned by the authenticated user.",
)


def _display_devices(
    devices: list[dict[str, object]],
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """Display devices as JSON, YAML, or a Rich table.
    
    :param devices: The list of devices to display.
    :type devices: list[dict[str, object]]
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    if display_structured_output(
        devices,
        json_output=json_output,
        yaml_output=yaml_output,
        yaml_root="devices",
    ):
        return

    table = Table(title="Devices", expand=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", overflow="ellipsis")
    table.add_column("Created")
    table.add_column("Status")
    for device in devices:
        table.add_row(
            str(device.get("id", "")),
            str(device.get("name", "")),
            str(device.get("created_at") or "-"),
            "revoked" if device.get("revoked_at") is not None else "active",
        )
    Console().print(table)


def _display_device(
    device: dict[str, object],
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """Display one device as JSON, YAML, or a Rich table.
    
    :param device: The device to display.
    :type device: dict[str, object]
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    if display_structured_output(
        device,
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return

    table = Table(title=f"Device {device.get('id', '')}", expand=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green", overflow="ellipsis")
    for key, value in device.items():
        table.add_row(key, str(value if value is not None else "-"))
    Console().print(table)


@app.command("list")
def list_devices(
    json_output: bool = typer.Option(False, "--json", help="Output devices as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output devices as YAML."),
) -> None:
    """List devices owned by the authenticated user.
    
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)
    try:
        devices = resource_rows(
            request_configured_api(SpecificRequest(
                method=HTTPMethod.GET,
                endpoint="users/me/devices",
            )),
            "device",
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if not devices and not (json_output or yaml_output):
        typer.echo("No devices found.")
        return
    _display_devices(devices, json_output=json_output, yaml_output=yaml_output)


@app.command("get")
def get_device(
    device_id: int = typer.Option(..., "--id", help="Device ID to retrieve."),
    json_output: bool = typer.Option(False, "--json", help="Output the device as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output the device as YAML."),
) -> None:
    """Retrieve an owned device by ID.

    :param device_id: The ID of the device to retrieve.
    :type device_id: int
    :param json_output: Whether to output as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output as YAML.
    :type yaml_output: bool
    """
    validate_output_options(json_output, yaml_output)
    try:
        device = resource_object(
            request_configured_api(SpecificRequest(
                method=HTTPMethod.GET,
                endpoint=f"users/me/devices/{device_id}",
            )),
            "device",
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    _display_device(device, json_output=json_output, yaml_output=yaml_output)


@app.command("add")
def add_device(
    file_path: Path = typer.Option(..., "--file", help="JSON or YAML device data file."),
) -> None:
    """Add a device from a JSON or YAML file.

    :param file_path: The path to the JSON or YAML device data file.
    :type file_path: Path
    """
    device_data = load_data_file(file_path, "device")
    try:
        device = resource_object(
            request_configured_api(SpecificRequest(
                method=HTTPMethod.POST,
                endpoint="users/me/devices",
                json_body=device_data,
            )),
            "device",
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Device {device.get('id', '')} added successfully.")


@app.command("delete")
def delete_device(
    device_id: int = typer.Option(..., "--id", help="Device ID to revoke."),
) -> None:
    """Revoke an owned device and its active leases.

    :param device_id: The ID of the device to revoke.
    :type device_id: int
    """
    if not typer.confirm(f"Revoke device {device_id} and its leases?"):
        raise typer.Exit(code=1)
    try:
        request_configured_api(SpecificRequest(
            method=HTTPMethod.DELETE,
            endpoint=f"users/me/devices/{device_id}",
        ))
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Device {device_id} revoked successfully.")
