"""WireGuard backend commands.

.. CLI::
    - `leases` for managing WireGuard peers as TTL-LAMa leases.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""

import typer

from .peers import app as leases_app

app = typer.Typer(
	no_args_is_help=True,
	help="Manage WireGuard peers as TTL-LAMa leases.",
)
app.add_typer(leases_app, name="leases")
