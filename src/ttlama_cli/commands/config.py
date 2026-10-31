"""Commands for TTL-LAMa CLI configuration.

.. prefix:: `ttlama config`

.. CLI::
    - `set-server`: Configure the server for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import typer
from ..config_store import save_server_config

app = typer.Typer(
    no_args_is_help=True,
    help="Configuration commands for TTL-LAMa CLI.",
)

@app.command("set-server")
def config_server(
    url: str = typer.Argument(
        ...,
        help="Server URL for TTL-LAMa CLI configuration.",
    ),
    port: int = typer.Option(
        default=8080,
        help="Server port for TTL-LAMa CLI configuration.",
    )
) -> None:
    """Configure the server for TTL-LAMa CLI.

    :param url: Server URL for TTL-LAMa CLI configuration.
    :type url: str
    :param port: Server port for TTL-LAMa CLI configuration.
    :type port: int
    """
    typer.echo(f"Configuring server with URL: {url}:{port}")
    save_server_config(url, port)
    typer.echo("Server configuration saved.")
