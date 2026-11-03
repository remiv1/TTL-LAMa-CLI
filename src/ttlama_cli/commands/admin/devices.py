"""Device management commands for the TTL-LAMa CLI.

.. CLI:: ``ttlama admin devices``
    - ``list``: list devices with optional lease and profile filters.
    - ``get``: retrieve a device.
    - ``update``: update device metadata from a JSON or YAML file.
    - ``block``: block a device and revoke its active leases.
    - ``delete``: logically delete a device and revoke its active leases.

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
    get_server_and_token as _get_server_and_token,
    load_data_file as _load_data_file,
    resource_object,
    resource_rows,
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

devices_app = typer.Typer(
    no_args_is_help=True,
    help="Device management commands for the TTL-LAMa CLI.",
)


def _load_device_file(file_path: Path) -> dict[str, JSONValue]:
    """Load a device update body from a JSON or YAML file.

    :param file_path: The path to the device data file.
    :type file_path: Path
    :returns: The parsed device update body.
    :rtype: dict[str, JSONValue]
    """
    return _load_data_file(file_path, "device")


def _create_filters(
    lease: int | None = None,
    profile: int | None = None,
) -> dict[str, int] | None:
    """Create combined device relationship filters.

    :param lease: The lease ID to filter by.
    :type lease: int | None
    :param profile: The profile ID to filter by.
    :type profile: int | None
    :returns: The query parameters, or None when no filters are set.
    :rtype: dict[str, int] | None
    """
    filters = {
        key: value
        for key, value in {"lease": lease, "profile": profile}.items()
        if value is not None
    }
    return filters or None


def _device_update_data(response: object) -> dict[str, object]:
    """Extract the fields accepted by the device update endpoint.

    :param response: The device object returned by the API.
    :type response: object
    :returns: The name and public key accepted by the update API.
    :rtype: dict[str, object]
    """
    device = resource_object(response, "device")
    name = device.get("name")
    public_key = device.get("public_key")
    if not isinstance(name, str) or not isinstance(public_key, str):
        raise APIError("The API device response has invalid update fields.")
    return {"name": name, "public_key": public_key}


@devices_app.command("ls")
def list_devices(
    lease: int | None = typer.Option(None, "--lease", help="Filter by lease ID."),
    profile: int | None = typer.Option(None, "--profile", help="Filter by profile ID."),
    json_output: bool = typer.Option(False, "--json", help="Output devices as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output devices as YAML."),
) -> None:
    """List devices, optionally filtered by lease or profile.

    :param lease: Filter by lease ID.
    :type lease: int | None
    :param profile: Filter by profile ID.
    :type profile: int | None
    :param json_output: Whether to output devices as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output devices as YAML.
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
                endpoint="admin/devices",
                params=_create_filters(lease=lease, profile=profile),
            ),
        )
        devices = resource_rows(response, "device")
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if not devices:
        typer.echo("No devices found.")
        raise typer.Exit(code=1)
    if display_structured_output(
        devices,
        json_output=json_output,
        yaml_output=yaml_output,
        yaml_root="devices",
    ):
        return

    table = Table(title="Devices", expand=True)
    table.add_column("Device ID", style="cyan", no_wrap=True)
    table.add_column("User ID", overflow="ellipsis")
    table.add_column("Name", style="green", overflow="ellipsis")
    table.add_column("Created", overflow="ellipsis")
    table.add_column("Status", justify="center")
    for device in devices:
        status = "blocked" if device.get("revoked_at") is not None else "active"
        table.add_row(
            str(device.get("id", "")),
            str(device.get("user_id", "")),
            str(device.get("name", "")),
            str(device.get("created_at", "")),
            status,
        )
    Console().print(table)


@devices_app.command("get")
def get_device(
    device_id: int = typer.Option(..., "--device", help="Device ID to retrieve."),
    json_output: bool = typer.Option(False, "--json", help="Output editable fields as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output editable fields as YAML."),
) -> None:
    """Retrieve a device and display its details.

    :param device_id: The ID of the device to retrieve.
    :type device_id: int
    :param json_output: Whether to output editable fields as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output editable fields as YAML.
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
                endpoint=f"admin/devices/{device_id}",
            ),
        )
        device = resource_object(response, "device")
        update_data = _device_update_data(device)
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if display_structured_output(
        update_data,
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return

    table = Table(title=f"Device {device_id}", expand=True)
    table.add_column("Field", style="cyan", overflow="ellipsis")
    table.add_column("Value", style="green", overflow="ellipsis")
    for key in ("id", "user_id", "name", "public_key", "created_at", "revoked_at"):
        value = device.get(key)
        table.add_row(key, "-" if value is None else str(value))
    Console().print(table)


@devices_app.command("update")
def update_device(
    device_id: int = typer.Option(..., "--device", help="Device ID to update."),
    file_path: Path = typer.Option(..., "--file", help="JSON or YAML device update file."),
) -> None:
    """Update a device from a JSON or YAML file.

    :param device_id: The ID of the device to update.
    :type device_id: int
    :param file_path: The path to the device update file.
    :type file_path: Path
    """
    device_data = _load_device_file(file_path)
    server_url, server_port, token = _get_server_and_token()
    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.PATCH,
                endpoint=f"admin/devices/{device_id}",
                json_body=device_data,
            ),
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Device {device_id} updated successfully.")


@devices_app.command("block")
def block_device(
    device_id: int = typer.Option(..., "--device", help="Device ID to block."),
) -> None:
    """Block a device after confirmation and revoke its active leases.

    :param device_id: The ID of the device to block.
    :type device_id: int
    """
    if not typer.confirm(
        f"Block device {device_id} and revoke its active leases?",
        default=False,
    ):
        typer.echo("Device was not blocked.", err=True)
        raise typer.Exit(code=1)

    server_url, server_port, token = _get_server_and_token()
    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.POST,
                endpoint=f"admin/devices/{device_id}/block",
            ),
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Device {device_id} blocked; active leases were revoked.")


@devices_app.command("delete")
def delete_device(
    device_id: int = typer.Option(..., "--device", help="Device ID to delete."),
) -> None:
    """Logically delete a device after confirmation.

    Deletion revokes the device and its active leases but retains its history.

    :param device_id: The ID of the device to delete.
    :type device_id: int
    """
    if not typer.confirm(
        f"Delete device {device_id}, revoke its active leases, and retain its history?",
        default=False,
    ):
        typer.echo("Device was not deleted.", err=True)
        raise typer.Exit(code=1)

    server_url, server_port, token = _get_server_and_token()
    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.DELETE,
                endpoint=f"admin/devices/{device_id}",
            ),
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(
        f"Device {device_id} deleted (revoked); active leases were revoked and history retained."
    )
