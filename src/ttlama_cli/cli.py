"""CLI to administrate TTL-LAMa.

.. functions::
    - `main`: Entrypoint for the TTL-LAMa CLI.

.. cli::
    - `callback`: Callback for the TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 0.1.0
"""

from __future__ import annotations

from importlib.metadata import version, metadata

import typer

from .commands.auth import app as auth_app
from .commands.config import app as config_app, global_config_app
from .commands.admin import app as admin_app
from .commands.user import app as user_app
from .commands.backend import app as backend_app

app = typer.Typer(
    no_args_is_help=True,
    help="CLI to administrate TTL-LAMa.",
)
app.add_typer(auth_app, name="auth")
app.add_typer(config_app, name="config")
app.add_typer(global_config_app, name="global-config")
app.add_typer(admin_app, name="admin")
app.add_typer(user_app, name="user")
app.add_typer(backend_app, name="backend")

def show_version(value: bool) -> bool:
    """Show the version of the TTL-LAMa CLI if the flag is set."""
    if value:
        name_mail = metadata('ttlama_cli')['Author-email'].split('|')
        name = name_mail[0].replace("\"", "").strip()
        mail = name_mail[1]
        version_str = version('ttlama_cli')
        url = metadata('ttlama_cli')['Project-URL']
        print(f"TTL-LAMa-CLI                 {' ' * 20}{version_str}")
        print(f"Developped and maintained by {' ' * 20}{name}")
        print(f"Read more in                 {' ' * 20}{url}")
        print(f"Contact for more at          {' ' * 20}{mail}")
        raise typer.Exit()
    return value

def main() -> None:
    """Entrypoint for the TTL-LAMa CLI.
    
    .. note:: This is the main entrypoint for the TTL-LAMa CLI. Use the `ttlama` command
    to invoke it.
    """
    app()

@app.callback()
def callback(
    version_flag: bool = typer.Option(  # pylint: disable=W0613
        False,
        "--version",
        "-v",
        is_eager=True,
        callback=show_version,
        help="Show the version of the TTL-LAMa CLI.",
    )
) -> None:
    """Callback for the TTL-LAMa CLI."""
    pass    # pylint: disable=W0107
