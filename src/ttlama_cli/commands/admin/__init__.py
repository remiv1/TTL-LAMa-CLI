"""Admin commands for the TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 0.1.0
"""
from __future__ import annotations

import typer

from .users import users_app

app = typer.Typer(
    no_args_is_help=True,
    help="Admin commands for the TTL-LAMa CLI.",
)
app.add_typer(users_app, name="users")
