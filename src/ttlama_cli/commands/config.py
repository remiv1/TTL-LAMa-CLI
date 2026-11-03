"""Commands for TTL-LAMa CLI configuration.

.. prefixes::
    - `ttlama config`
    - `ttlama global-config`

.. CLI::
    - `set-server`: Configure the server for TTL-LAMa CLI.
    - `get`: Read the current application configuration.
    - `diff`: Compare a candidate configuration with the server configuration.
    - `validate`: Validate a candidate configuration.
    - `apply`: Apply a candidate configuration.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn, cast

import typer
import yaml
from rich.console import Console
from rich.table import Table
from yaml import YAMLError

from ..api_client import request_api
from ..config_store import save_server_config
from ..exc import APIError, AuthenticationError, AuthorizationError, handle_api_error
from ..objects import HTTPMethod, ServerParameters, SpecificRequest
from ..objects.requests import JSONValue
from ..utils import json_to_yaml
from . import get_server_and_token

VALIDATION_RESPONSE_ERROR = "The API validation response is invalid."
REDACTED = "[REDACTED]"
SECRET_PATHS = {
    "app.secret_key",
    "auth.admin.password",
    "auth.oidc.client_secret",
    "database.password",
}

app = typer.Typer(
    no_args_is_help=True,
    help="Configuration commands for TTL-LAMa CLI.",
)
global_config_app = typer.Typer(
    no_args_is_help=True,
    help="Read and manage the application configuration.",
)


def _api_error(message: str) -> NoReturn:
    """Report an invalid API response without exposing a traceback."""
    error = APIError(message)
    handle_api_error(error)
    raise error


def _load_candidate(file_path: Path) -> dict[str, JSONValue]:
    """Load a JSON-compatible YAML configuration mapping."""
    try:
        parsed: object = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        data = json.loads(json.dumps(parsed, ensure_ascii=False))
    except (OSError, YAMLError, TypeError, ValueError, RecursionError) as error:
        typer.echo(f"Unable to read a valid configuration file: {error}", err=True)
        raise typer.Exit(code=1) from error

    if not isinstance(data, dict):
        typer.echo("The configuration file must contain an object at the top level.", err=True)
        raise typer.Exit(code=1)
    return cast(dict[str, JSONValue], data)


def _request_global_config(
    method: HTTPMethod,
    endpoint: str,
    candidate: dict[str, JSONValue] | None = None,
) -> object:
    """Send a request to the global configuration endpoints."""
    server_url, server_port, token = get_server_and_token()
    try:
        return request_api(
            server=ServerParameters(server_url=server_url, server_port=server_port),
            token=token,
            specific_request=SpecificRequest(
                method=method,
                endpoint=f"global-config{endpoint}",
                json_body=candidate,
            ),
        )
    except (AuthenticationError, AuthorizationError, APIError) as error:
        handle_api_error(error)
        raise typer.Exit(code=1) from error


def _configuration_response(response: object) -> dict[str, JSONValue]:
    """Validate an API response containing a configuration mapping."""
    if not isinstance(response, dict):
        _api_error("The API response isn't a configuration object.")
    return cast(dict[str, JSONValue], response)


def _validation_errors(candidate: dict[str, JSONValue]) -> list[str]:
    """Validate a candidate using the server-side settings models."""
    response = _request_global_config(HTTPMethod.POST, "/validate", candidate)
    if not isinstance(response, dict):
        _api_error(VALIDATION_RESPONSE_ERROR)
    result = cast(dict[str, object], response)
    valid = result.get("valid")
    errors = result.get("errors")
    if not isinstance(valid, bool) or not isinstance(errors, list):
        _api_error(VALIDATION_RESPONSE_ERROR)
    if any(not isinstance(error, str) for error in cast(list[object], errors)):
        _api_error(VALIDATION_RESPONSE_ERROR)
    if not valid and not errors:
        return ["The API rejected the configuration without details."]
    return cast(list[str], errors)


def _unchanged_secret_paths(candidate: dict[str, JSONValue]) -> set[str]:
    """Ask the server which direct candidate secrets are unchanged."""
    response = _request_global_config(HTTPMethod.POST, "/compare", candidate)
    if not isinstance(response, dict):
        _api_error("The API secret comparison response is invalid.")
    unchanged = cast(dict[str, object], response).get("unchanged_secrets")
    if not isinstance(unchanged, list) or any(
        not isinstance(path, str) or path not in SECRET_PATHS
        for path in cast(list[object], unchanged)
    ):
        _api_error("The API secret comparison response is invalid.")
    return set(cast(list[str], unchanged))

def _flatten(value: object, prefix: str = "") -> dict[str, object]:
    """Flatten nested mappings into dotted paths while retaining list values."""
    if not isinstance(value, dict) or not value:
        return {prefix: value} if prefix else {}

    flattened: dict[str, object] = {}
    for key, child in cast(dict[str, object], value).items():
        path = f"{prefix}.{key}" if prefix else str(key)
        flattened.update(_flatten(child, path))
    return flattened


def _render_value(value: object) -> str:
    """Render a diff value as compact JSON text."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _is_unchanged(
    path: str,
    old_value: object,
    new_value: object,
    unchanged_secrets: set[str],
) -> bool:
    """Determine equality using server-side comparison for redacted secrets."""
    return old_value == new_value or (
        path in SECRET_PATHS and path in unchanged_secrets
    )


def _display_value(path: str, value: object) -> object:
    """Hide direct secret values in diff output."""
    return REDACTED if path in SECRET_PATHS else value


def _display_diff(
    current: dict[str, JSONValue],
    candidate: dict[str, JSONValue],
    *,
    check_all: bool,
    unchanged_secrets: set[str] | None = None,
) -> int:
    """Display added, removed, changed, and optionally unchanged values."""
    unchanged_secrets = unchanged_secrets or set()
    current_values = _flatten(current)
    candidate_values = _flatten(candidate)
    table = Table(title="Global configuration changes", expand=True)
    table.add_column("Change", no_wrap=True)
    table.add_column("Path", style="cyan", overflow="ellipsis")
    table.add_column("Value", overflow="fold")

    changes = 0
    for path in sorted(current_values.keys() | candidate_values.keys()):
        in_current = path in current_values
        in_candidate = path in candidate_values
        old_value = current_values.get(path)
        new_value = candidate_values.get(path)
        is_unchanged = in_current and in_candidate and _is_unchanged(
            path,
            old_value,
            new_value,
            unchanged_secrets,
        )
        if is_unchanged:
            if check_all:
                table.add_row(
                    "Unchanged",
                    path,
                    _render_value(_display_value(path, old_value)),
                    style="dim",
                )
            continue
        if in_current:
            table.add_row(
                "Removed",
                path,
                _render_value(_display_value(path, old_value)),
                style="red",
            )
            changes += 1
        if in_candidate:
            table.add_row(
                "Added",
                path,
                _render_value(_display_value(path, new_value)),
                style="green",
            )
            changes += 1

    if changes or check_all:
        Console().print(table)
    return changes


def _report_validation(errors: list[str]) -> None:
    """Print validation errors and stop the command when the candidate is invalid."""
    if not errors:
        typer.echo("Configuration is valid.")
        return
    typer.echo("Configuration is invalid:", err=True)
    for error in errors:
        typer.echo(f"- {error}", err=True)
    raise typer.Exit(code=1)

@app.command("set-server")
def config_server(
    url: str = typer.Argument(
        ...,
        help="Server URL for TTL-LAMa CLI configuration.",
    ),
    port: int = typer.Option(
        default=8080,
        help="Server port for TTL-LAMa CLI configuration.",
    )
) -> None:
    """Configure the server for TTL-LAMa CLI.

    :param url: Server URL for TTL-LAMa CLI configuration.
    :type url: str
    :param port: Server port for TTL-LAMa CLI configuration.
    :type port: int
    """
    typer.echo(f"Configuring server with URL: {url}:{port}")
    save_server_config(url, port)
    typer.echo("Server configuration saved.")


@global_config_app.command("get")
def get_global_config(
    json_output: bool = typer.Option(False, "--json", help="Output the configuration as JSON."),
    yaml_output: bool = typer.Option(False, "--yaml", help="Output the configuration as YAML."),
) -> None:
    """Read and display the server's current application configuration."""
    if json_output and yaml_output:
        typer.echo("Choose only one output option: --json or --yaml.", err=True)
        raise typer.Exit(code=1)
    configuration = _configuration_response(
        _request_global_config(HTTPMethod.GET, "")
    )
    if json_output:
        typer.echo(json.dumps(configuration, ensure_ascii=False, indent=4))
        return
    if yaml_output:
        typer.echo(json_to_yaml(json.dumps(configuration, ensure_ascii=False)))
        return

    table = Table(title="Global configuration", expand=True)
    table.add_column("Path", style="cyan", overflow="ellipsis")
    table.add_column("Value", overflow="fold")
    for path, value in sorted(_flatten(configuration).items()):
        table.add_row(path, _render_value(value))
    Console().print(table)


@global_config_app.command("diff")
def diff_global_config(
    file_path: Path = typer.Option(..., "--file", exists=True, readable=True),
    check_all: bool = typer.Option(False, "--check-all", help="Include unchanged values."),
) -> None:
    """Compare a candidate file with the server configuration."""
    candidate = _load_candidate(file_path)
    current = _configuration_response(_request_global_config(HTTPMethod.GET, ""))
    _report_validation(_validation_errors(candidate))
    unchanged_secrets = _unchanged_secret_paths(candidate)
    changes = _display_diff(
        current,
        candidate,
        check_all=check_all,
        unchanged_secrets=unchanged_secrets,
    )
    if not changes:
        typer.echo("Configuration is already up to date.")


@global_config_app.command("validate")
def validate_global_config(
    file_path: Path = typer.Option(..., "--file", exists=True, readable=True),
) -> None:
    """Validate a candidate configuration file on the server."""
    candidate = _load_candidate(file_path)
    _report_validation(_validation_errors(candidate))


@global_config_app.command("apply")
def apply_global_config(
    file_path: Path = typer.Option(..., "--file", exists=True, readable=True),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and show changes only."),
) -> None:
    """Validate, show, and optionally persist a candidate configuration."""
    candidate = _load_candidate(file_path)
    current = _configuration_response(_request_global_config(HTTPMethod.GET, ""))
    _report_validation(_validation_errors(candidate))
    unchanged_secrets = _unchanged_secret_paths(candidate)
    changes = _display_diff(
        current,
        candidate,
        check_all=False,
        unchanged_secrets=unchanged_secrets,
    )
    if not changes:
        typer.echo("Configuration is already up to date.")
        return
    if dry_run:
        typer.echo("Dry run: no changes were applied.")
        return

    typer.confirm("Apply these configuration changes?", abort=True)
    response = _request_global_config(HTTPMethod.POST, "/apply", candidate)
    result = _configuration_response(response)
    if result.get("applied") is not True:
        _api_error("The API did not confirm the configuration update.")
    typer.echo("Configuration applied. Restart the server to activate the new settings.")
    warning = result.get("warning")
    if isinstance(warning, str) and warning:
        typer.echo(f"Warning: {warning}", err=True)
