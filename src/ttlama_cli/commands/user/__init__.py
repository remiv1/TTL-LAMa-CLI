"""Commands for the authenticated TTL-LAMa user.

.. prefix:: `ttlama user`

.. CLI::
    - `get` : Display the current user, devices, leases, and assigned profiles.
    - `devices` : Manage the user's devices.
    - `leases` : Manage the user's leases.
    - `profiles` : Manage the user's profiles.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0"""
from __future__ import annotations

import typer

from .devices import app as devices_app
from .get import get_user
from .leases import app as leases_app
from .profiles import app as profiles_app

app = typer.Typer(
    no_args_is_help=True,
    help="Commands for the authenticated TTL-LAMa user.",
)
app.command("get")(get_user)
app.add_typer(devices_app, name="devices")
app.add_typer(leases_app, name="leases")
app.add_typer(profiles_app, name="profiles")
