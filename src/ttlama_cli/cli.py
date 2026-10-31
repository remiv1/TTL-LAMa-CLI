"""CLI to administrate TTL-LAMa.

.. functions::
    - `main`: Entrypoint for the TTL-LAMa CLI.

.. cli::
    - `callback`: Callback for the TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 0.1.0
"""

from __future__ import annotations

import typer

from .commands.auth import app as auth_app
from .commands.config import app as config_app
from .commands.admin import app as admin_app
from .commands.user import app as user_app

app = typer.Typer(
    no_args_is_help=True,
    help="CLI to administrate TTL-LAMa.",
)
app.add_typer(auth_app, name="auth")
app.add_typer(config_app, name="config")
app.add_typer(admin_app, name="admin")
app.add_typer(user_app, name="user")


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
