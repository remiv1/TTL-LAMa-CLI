"""Admin commands for the TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 0.1.0
"""
from __future__ import annotations

import typer

from .devices import devices_app
from .leases import leases_app
from .profiles import profiles_app
from .users import users_app

app = typer.Typer(
    no_args_is_help=True,
    help="Admin commands for the TTL-LAMa CLI.",
)
app.add_typer(users_app, name="users")
app.add_typer(devices_app, name="devices")
app.add_typer(leases_app, name="leases")
app.add_typer(profiles_app, name="profiles")
