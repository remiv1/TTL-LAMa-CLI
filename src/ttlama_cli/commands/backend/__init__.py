"""Backend command group for local VPN operations.

.. CLI::
    - `wg` for WireGuard operations.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""

import typer

from .wireguard import app as wireguard_app

app = typer.Typer(
	no_args_is_help=True,
	help="Operate local VPN backends.",
)
app.add_typer(wireguard_app, name="wg")
