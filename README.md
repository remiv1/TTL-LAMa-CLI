# TTL-LAMa CLI

English | [Français](docs/README.fr.md)

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Typer](https://img.shields.io/badge/CLI-Typer-009688)](https://typer.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../LICENSE)

[![Logo](./docs/img/logo_300ppp.png)](./docs/img/logo_300ppp.png)

`ttlama` is the command-line interface for TTL-LAMa (Time-to-Live Lease Administration Manager). It lets users and administrators interact with a TTL-LAMa instance through its HTTP API, without relying on the web interface.

The CLI lives in the `cli/` directory and can evolve independently of the server. TTL-LAMa manages temporary network access as leases; the CLI is neither a VPN client nor a general-purpose network administration tool.

## Project status

The CLI is under development. Currently available commands let you configure the server address and authenticate with an internal account. Commands marked as planned below are targets for future implementation, not commands that can be used today.

| Group | Available commands | Planned commands |
| --- | --- | --- |
| `config` | `set-server` | — |
| `auth` | `login internal` | `login external`, `login oidc`, `logout`, `status` |
| `user` | — | View the user, their devices and leases, and the profiles available to them |
| `global-config` | — | `get`, `diff`, `validate`, `apply` |
| `admin users` | — | `list`, `get`, `create`, `update`, `delete`, `assign`, `unassign` |
| `admin devices` | — | `list`, `get`, `update`, `block`, `delete` |
| `admin leases` | — | `list`, `get`, `revoke` |
| `admin profiles` | — | `list`, `get`, `create`, `update`, `delete` |

Planned commands will cover the resources and operations exposed by the [v1 API](../src/api/v1/README.md) (see the github.com/remiv1/TTL-LAMa repository). Their filtering options and file formats will be defined as they are implemented.

## Installation and usage

The package is not yet published on PyPI. Once it is, it will be installable with `pip install ttlama-cli`.

Requirements: Python 3.12 or later and an instance of TTL-LAMa accessible over HTTP(S). From the `cli/` directory, install the package in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ttlama --help
```

Configure the instance. The URL includes the scheme and host; provide the port separately:

```bash
ttlama config set-server http://localhost --port 8080
```

Sign in with an internal account. The password is prompted for securely and is not passed as a command argument:

```bash
ttlama auth login internal --user admin
```

The command performs the CSRF exchange required by the API, then stores the access token returned by the server. It does not display the password or token.

## Configuration and credentials

The instance address and port are stored in `config.json` under the user configuration directory determined by `platformdirs` (for example, the XDG directory on Linux). The URL must use `http` or `https` and must not contain credentials, query parameters, or a fragment.

The access token is stored in the system keyring through `keyring`. Its entry is associated with the instance and username, so the token is not written to the JSON configuration file.

## Code layout

- `src/ttlama_cli/cli.py` defines the `ttlama` command and its groups.
- `src/ttlama_cli/commands/` contains the Typer commands, including `auth` and `config`.
- `src/ttlama_cli/api_client.py` makes HTTP requests to the API.
- `src/ttlama_cli/config_store.py` validates and persists the configured instance.
- `src/ttlama_cli/token_store.py` encapsulates access to the system keyring.
- `tests/` contains the unit and integration tests.

## Unit tests

Install the test dependencies, then run the test suite from `cli/`:

```bash
python -m pip install -e '.[test]'
python -m pytest tests/
```

## Integration tests

The launcher starts an ephemeral instance from `ghcr.io/remiv1/ttl-lama:latest`, then runs authentication commands against the real server:

```bash
./scripts/test-integration.sh
```

The launcher requires Podman Compose and access to the GHCR image. It checks that internal authentication succeeds and an incorrect password is rejected. The test server uses dedicated credentials, the keyring is replaced with in-memory storage, and no host volumes are mounted. The Compose project containers are stopped and removed when the script finishes.
