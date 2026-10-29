"""CLI to administrate TTL-LAMa.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 0.1.0
"""

from __future__ import annotations

import typer

from .commands.auth import app as auth_app
from .commands.config import app as config_app

app = typer.Typer(
    no_args_is_help=True,
    help="CLI to administrate TTL-LAMa.",
)
app.add_typer(auth_app, name="auth")
app.add_typer(config_app, name="config")


def main() -> None:
    """Entrypoint for the TTL-LAMa CLI.
    
    .. note:: This is the main entrypoint for the TTL-LAMa CLI. Use the `ttlama` command
    to invoke it.
    """
    app()

@app.callback()
def callback() -> None:
    """Callback for the TTL-LAMa CLI."""
    pass    # pylint: disable=W0107
