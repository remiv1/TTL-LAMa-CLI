"""Display the authenticated user's overview.

.. prefix:: `ttlama user`

.. CLI::
    - `get` : Display the authenticated user's overview.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from .. import (
    display_profiles,
    display_structured_output,
    get_server_and_token,
    profile_rows,
    request_user_overview,
    validate_output_options,
)
from ...exc import APIError, AuthenticationError, AuthorizationError, handle_api_error


def get_user(   # pylint: disable=R0914
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output as YAML."),
) -> None:
    """Display the current user, devices, leases, and assigned profiles."""
    validate_output_options(json_output, yaml_output)
    server_url, server_port, token = get_server_and_token()
    try:
        overview = request_user_overview(server_url, server_port, token)
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if display_structured_output(
        overview,
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return

    user = cast(dict[str, object], overview["user"])
    user_table = Table(title="User", expand=True)
    user_table.add_column("Field", style="cyan")
    user_table.add_column("Value", style="green", overflow="ellipsis")
    for key in ("id", "username", "email"):
        user_table.add_row(key, str(user.get(key) or "-"))
    user_table.add_row("Administrator", "yes" if user.get("is_admin") else "no")
    Console().print(user_table)

    devices = cast(list[dict[str, object]], overview["devices"])
    device_table = Table(title="Devices", expand=True)
    device_table.add_column("ID", style="cyan", no_wrap=True)
    device_table.add_column("Name", style="green", overflow="ellipsis")
    device_table.add_column("Created")
    device_table.add_column("Status")
    for device in devices:
        device_table.add_row(
            str(device.get("id", "")),
            str(device.get("name", "")),
            str(device.get("created_at") or "-"),
            "revoked" if device.get("revoked_at") is not None else "active",
        )
    Console().print(device_table)

    leases = cast(list[dict[str, object]], overview["leases"])
    lease_table = Table(title="Leases", expand=True)
    lease_table.add_column("ID", style="cyan", no_wrap=True)
    lease_table.add_column("Device ID")
    lease_table.add_column("Profile ID")
    lease_table.add_column("Ends")
    lease_table.add_column("Status")
    for lease in leases:
        lease_table.add_row(
            str(lease.get("id", "")),
            str(lease.get("device_id", "")),
            str(lease.get("profile_id", "")),
            str(lease.get("ended_at") or "-"),
            str(lease.get("status", "")),
        )
    Console().print(lease_table)

    display_profiles(
        profile_rows(overview["profiles"]),
        json_output=False,
        yaml_output=False,
    )
