"""Lease management commands for the TTL-LAMa CLI.

.. CLI:: ``ttlama admin leases``
    - ``list``: list leases with optional user, device, profile, and status filters.
    - ``get``: retrieve a lease.
    - ``revoke``: revoke a lease while retaining its history.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from enum import Enum

import typer
from rich.console import Console
from rich.table import Table

from .. import (
    display_structured_output,
    get_server_and_token as _get_server_and_token,
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

leases_app = typer.Typer(
    no_args_is_help=True,
    help="Lease management commands for the TTL-LAMa CLI.",
)


class LeaseStatus(str, Enum):
    """Statuses accepted by the lease list endpoint."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


def _create_filters(
    user: str | None = None,
    device: int | None = None,
    profile: int | None = None,
    status: LeaseStatus | None = None,
) -> dict[str, str | int] | None:
    """Create combined lease filters for the API request.

    :param user: Filter by user UUID.
    :type user: str | None
    :param device: Filter by device ID.
    :type device: int | None
    :param profile: Filter by profile ID.
    :type profile: int | None
    :param status: Filter by lease lifecycle status.
    :type status: LeaseStatus | None
    :returns: The query parameters, or None when no filters are set.
    :rtype: dict[str, str | int] | None
    """
    filters: dict[str, str | int] = {
        key: value
        for key, value in {
            "user": user,
            "device": device,
            "profile": profile,
            "status": status.value if status is not None else None,
        }.items()
        if value is not None
    }
    return filters or None


@leases_app.command(
    "list",
    help="List leases, optionally filtered by user, device, profile, or status.",
)
def list_leases(    # pylint: disable=R0913, R0917
    user: str | None = typer.Option(None, "--user", help="Filter by user UUID."),
    device: int | None = typer.Option(None, "--device", help="Filter by device ID."),
    profile: int | None = typer.Option(None, "--profile", help="Filter by profile ID."),
    status: LeaseStatus | None = typer.Option(
        None,
        "--status",
        help="Filter by status: active, expired, or revoked.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output leases as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output leases as YAML."),
) -> None:
    """List leases, optionally filtered by user, device, profile, or status.

    :param user: Filter by user UUID.
    :type user: str | None
    :param device: Filter by device ID.
    :type device: int | None
    :param profile: Filter by profile ID.
    :type profile: int | None
    :param status: Filter by lease lifecycle status.
    :type status: LeaseStatus | None
    :param json_output: Whether to output leases as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output leases as YAML.
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
                endpoint="admin/leases",
                params=_create_filters(
                    user=user,
                    device=device,
                    profile=profile,
                    status=status,
                ),
            ),
        )
        leases = resource_rows(response, "lease")
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if not leases:
        typer.echo("No leases found.")
        raise typer.Exit(code=1)
    if display_structured_output(
        leases,
        json_output=json_output,
        yaml_output=yaml_output,
        yaml_root="leases",
    ):
        return

    table = Table(title="Leases", expand=True)
    table.add_column("Lease ID", style="cyan", no_wrap=True)
    table.add_column("User ID", overflow="ellipsis")
    table.add_column("Device ID", justify="right")
    table.add_column("Profile ID", justify="right")
    table.add_column("Created", overflow="ellipsis")
    table.add_column("Ends", overflow="ellipsis")
    table.add_column("Status", justify="center")
    for lease in leases:
        table.add_row(
            str(lease.get("id", "")),
            str(lease.get("user_id", "")),
            str(lease.get("device_id", "")),
            str(lease.get("profile_id", "")),
            str(lease.get("created_at", "")),
            str(lease.get("ended_at", "")),
            str(lease.get("status", "")),
        )
    Console().print(table)


@leases_app.command("get", help="Retrieve a lease and display all of its fields.")
def get_lease(
    lease_id: int = typer.Option(..., "--lease", help="Lease ID to retrieve."),
    json_output: bool = typer.Option(False, "--json", help="Output the lease as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output the lease as YAML."),
) -> None:
    """Retrieve a lease and display all of its fields.

    :param lease_id: The ID of the lease to retrieve.
    :type lease_id: int
    :param json_output: Whether to output the lease as JSON.
    :type json_output: bool
    :param yaml_output: Whether to output the lease as YAML.
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
                endpoint=f"admin/leases/{lease_id}",
            ),
        )
        lease = resource_object(response, "lease")
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return

    if display_structured_output(
        lease,
        json_output=json_output,
        yaml_output=yaml_output,
    ):
        return

    table = Table(title=f"Lease {lease_id}", expand=True)
    table.add_column("Field", style="cyan", overflow="ellipsis")
    table.add_column("Value", style="green", overflow="ellipsis")
    for key, value in lease.items():
        table.add_row(key, "-" if value is None else str(value))
    Console().print(table)


@leases_app.command(
    "revoke",
    help="Revoke a lease after confirmation while retaining its history.",
)
def revoke_lease(
    lease_id: int = typer.Option(..., "--lease", help="Lease ID to revoke."),
) -> None:
    """Revoke a lease after confirmation while retaining its history.

    :param lease_id: The ID of the lease to revoke.
    :type lease_id: int
    """
    if not typer.confirm(
        f"Revoke lease {lease_id} and retain its history?",
        default=False,
    ):
        typer.echo("Lease was not revoked.", err=True)
        raise typer.Exit(code=1)

    server_url, server_port, token = _get_server_and_token()
    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=HTTPMethod.POST,
                endpoint=f"admin/leases/{lease_id}/revoke",
            ),
        )
    except (AuthorizationError, AuthenticationError, APIError) as error:
        handle_api_error(error)
        return
    typer.echo(f"Lease {lease_id} revoked; history retained.")
