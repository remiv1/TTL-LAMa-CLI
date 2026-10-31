"""Commands for TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import json
from typing import cast

import typer
from rich.console import Console
from rich.table import Table

from ..api_client import authenticate_internal, request_api
from ..config_store import load_server_config
from ..token_store import delete_access_token, get_access_token, save_access_token
from ..exc import (
    APIError, AuthenticationError, AuthorizationError, TokenStorageError,
)
from ..objects import HTTPMethod, ServerParameters, SpecificRequest
from ..utils import json_to_yaml

INVALID_RESPONSE = "La réponse de statut de l’API est invalide."

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
            token,
        )
    except (APIError, AuthenticationError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Connexion réussie. Jeton enregistré dans le trousseau système.")


@app.command("logout")
def logout() -> None:
    """Revoke the current session and remove its local token."""
    try:
        server_url, server_port = load_server_config()
        token = get_access_token(server_url, server_port)
    except (FileNotFoundError, ValueError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    if not token:
        typer.echo("Aucune session active. Déjà déconnecté.")
        return

    try:
        request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                endpoint="auth/logout",
                method=HTTPMethod.POST,
            ),
        )
    except AuthenticationError:
        try:
            delete_access_token(server_url, server_port)
        except TokenStorageError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from None
        typer.echo("La session était déjà inactive. Jeton local supprimé.")
        return
    except (APIError, AuthorizationError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    try:
        delete_access_token(server_url, server_port)
    except TokenStorageError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None
    typer.echo("Déconnexion réussie. Jeton local supprimé.")


def _status_payload(response: object) -> dict[str, object]:
    """Validate and restrict the identity and session data returned by the API."""
    if not isinstance(response, dict):
        raise APIError(INVALID_RESPONSE)
    response_data = cast(dict[str, object], response)
    raw_user = response_data.get("user")
    raw_sessions = response_data.get("sessions")
    if not isinstance(raw_user, dict) or not isinstance(raw_sessions, list):
        raise APIError(INVALID_RESPONSE)

    user_data = cast(dict[str, object], raw_user)
    user = {
        key: user_data.get(key)
        for key in ("id", "username", "email", "is_admin")
    }
    sessions: list[dict[str, str]] = []
    for raw_session in cast(list[object], raw_sessions):
        if not isinstance(raw_session, dict):
            raise APIError(INVALID_RESPONSE)
        session_data = cast(dict[str, object], raw_session)
        expiration = session_data.get("expires_at")
        if not isinstance(expiration, str):
            raise APIError(INVALID_RESPONSE)
        sessions.append({"expires_at": expiration})

    return {
        "session": "active" if sessions else "inactive",
        "user": user,
        "sessions": sessions,
    }


def _display_status(
    status_data: dict[str, object],
    *,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """Display status as JSON, YAML, or a Rich table."""
    if json_output:
        typer.echo(json.dumps(status_data, ensure_ascii=False, indent=2))
        return
    if yaml_output:
        typer.echo(json_to_yaml(json.dumps(status_data, ensure_ascii=False)))
        return

    typer.echo()
    table = Table(title="État de l’authentification", expand=True)
    table.add_column("Élément", style="cyan")
    table.add_column("Valeur", style="green")
    table.add_row("Session", str(status_data["session"]))
    user = cast(dict[str, object] | None, status_data["user"])
    if user is not None:
        table.add_row("Utilisateur", str(user["username"] or "-"))
        table.add_row("E-mail", str(user["email"] or "-"))
        table.add_row("Administrateur", "oui" if user["is_admin"] else "non")
    sessions = cast(list[dict[str, str]], status_data["sessions"])
    table.add_row("Sessions actives", str(len(sessions)))
    for index, session in enumerate(sessions, start=1):
        table.add_row(f"Expiration {index}", session["expires_at"])
    Console().print(table)


@app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Output status as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output status as YAML."),
    check_connected: bool = typer.Option(
        False,
        "--check-connected",
        help="Exit with status 1 when no active session is available.",
    ),
) -> None:
    """Display the current identity and active session expirations."""
    if json_output and yaml_output:
        typer.echo("Choisissez une seule option de sortie : --json ou --yaml.", err=True)
        raise typer.Exit(code=1)

    try:
        server_url, server_port = load_server_config()
        token = get_access_token(server_url, server_port)
    except (FileNotFoundError, ValueError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    status_data: dict[str, object]
    if token:
        try:
            response = request_api(
                server=ServerParameters(server_url=server_url, server_port=server_port),
                token=token,
                specific_request=SpecificRequest(
                    endpoint="users/me",
                    method=HTTPMethod.GET,
                ),
            )
            status_data = _status_payload(response)
        except AuthenticationError:
            typer.echo("Jeton invalide ou expiré. Reconnectez-vous.", err=True)
            raise typer.Exit(code=1) from None
        except (APIError, AuthorizationError) as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from None
    else:
        status_data = {"session": "inactive", "user": None, "sessions": []}

    _display_status(status_data, json_output=json_output, yaml_output=yaml_output)
    if check_connected and status_data["session"] != "active":
        raise typer.Exit(code=1)


@app.command("password-chg")
def change_password() -> None:
    """Change the password of the authenticated account."""
    try:
        server_url, server_port = load_server_config()
        token = get_access_token(server_url, server_port)
        if not token:
            raise TokenStorageError("Aucun jeton d’accès n’est enregistré pour cette instance.")

        current_password = typer.prompt("Mot de passe actuel", hide_input=True)
        new_password = typer.prompt("Nouveau mot de passe", hide_input=True)
        confirmation = typer.prompt("Confirmer le nouveau mot de passe", hide_input=True)
        if new_password != confirmation:
            typer.echo("Les nouveaux mots de passe ne correspondent pas.", err=True)
            raise typer.Exit(code=1)

        request_api(
            ServerParameters(server_url=server_url, server_port=server_port),
            token,
            SpecificRequest(
                endpoint="users/me/password",
                method=HTTPMethod.PATCH,
                json_body={
                    "current_password": current_password,
                    "new_password": new_password,
                },
            ),
        )
    except (FileNotFoundError, ValueError, APIError, AuthenticationError,
            AuthorizationError, TokenStorageError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Mot de passe modifié. Reconnectez-vous ; toutes les sessions sont révoquées.")
