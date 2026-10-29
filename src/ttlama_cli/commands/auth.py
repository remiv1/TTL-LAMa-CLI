"""Commands for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import typer

from ..api_client import authenticate_internal
from ..config_store import load_server_config
from ..token_store import save_access_token
from ..exc import APIError, AuthenticationError, TokenStorageError

app = typer.Typer(
    no_args_is_help=True,
    help="Authentication to a TTL-LAMa.",
)
login_app = typer.Typer(
    no_args_is_help=True,
    help="Login to TTL-LAMa.",
)
app.add_typer(login_app, name="login")

@login_app.command("internal")
def login_internal(
    user: str = typer.Option(
        ...,
        "--user",
        help="Username for internal login.",
    ),
) -> None:
    """Connect with an internal account to a TTL-LAMa session."""
    try:
        server_url, server_port = load_server_config()
        token = authenticate_internal(
            server_url,
            server_port,
            user,
            typer.prompt("Password", hide_input=True),
        )
        save_access_token(
            server_url,
            server_port,
            user,
            token,
        )
    except (APIError, AuthenticationError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Connexion réussie. Jeton enregistré dans le trousseau système.")
