# TTL-LAMa CLI

English | [Français](docs/README.fr.md)

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Typer](https://img.shields.io/badge/CLI-Typer-009688)](https://typer.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../LICENSE)

[![Logo](./docs/img/logo_300ppp.png)](./docs/img/logo_300ppp.png)

`ttlama` is the command-line interface for TTL-LAMa (Time-to-Live Lease Administration Manager). It lets users and administrators interact with a TTL-LAMa instance through its HTTP API, without relying on the web interface.

The CLI lives in the `cli/` directory and can evolve independently of the server. TTL-LAMa manages temporary network access as leases; the CLI is neither a VPN client nor a general-purpose network administration tool.

## Project status

The CLI is under development. Currently available commands let you configure the server address, authenticate with an internal account, check and close the current session, change the signed-in user's password, and manage users and profiles. Commands marked as planned below are targets for future implementation, not commands that can be used today.

| Group | Available commands | Planned commands |
| --- | --- | --- |
| `config` | `set-server` | — |
| `auth` | `login internal`, `logout`, `password-chg`, `status` | `login external`, `login oidc` |
| `user` | — | View the user, their devices and leases, and the profiles available to them |
| `global-config` | — | `get`, `diff`, `validate`, `apply` |
| `admin users` | `list`, `get`, `create`, `update`, `delete` | `assign`, `unassign` |
| `admin devices` | — | `list`, `get`, `update`, `block`, `delete` |
| `admin leases` | — | `list`, `get`, `revoke` |
| `admin profiles` | `list`, `get`, `create`, `update`, `delete` | — |

Remaining planned commands will cover the resources and operations exposed by the [v1 API](../src/api/v1/README.md) (see the github.com/remiv1/TTL-LAMa repository). Their filtering options and file formats will be defined as they are implemented.

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

Change the password of the signed-in account. The current password and the new password are prompted for securely, with a second prompt to confirm the new password. After success, all of the account's sessions are revoked, including the CLI token; sign in again to store a new token.

```bash
ttlama auth password-chg
```

Inspect the current session, including active session expirations, or close the session used by this CLI instance:

```bash
ttlama auth status
ttlama auth status --json
ttlama auth status --yaml
ttlama auth status --check-connected
ttlama auth logout
```

`status` does not display access tokens or their hashes. With no locally stored token it reports a disconnected state and exits successfully; use `--check-connected` to return a nonzero exit code instead. `logout` revokes only the current CLI session. It removes the local token after success, and also cleans up a token the server reports as invalid; a server/network error keeps the token so the operation can be retried. JSON and YAML status output contain `session` (`active` or `inactive`), `user` (`null` without a local token; otherwise `id`, `username`, `email`, and `is_admin`), and `sessions`, a list of `expires_at` timestamps.

## Configuration and credentials

The instance address and port are stored in `config.json` under the user configuration directory determined by `platformdirs` (for example, the XDG directory on Linux). The URL must use `http` or `https` and must not contain credentials, query parameters, or a fragment.

The access token is stored in the system keyring through `keyring`, in one entry per configured instance. It is not written to the JSON configuration file. A password change revokes this token on the server; the next successful login replaces the local token.

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

## Command tree

Here is the target command tree for the `ttlama` command:

```md
ttlama
 ├── auth → **Authentication** → **_Who am I ?_**
 │    ├── login
 │    │     ├── internal --user <username>
 │    │     ├── external --user <username>
 │    │     └── oidc --user <username>
 │    │
 │    ├── logout
 │    ├── password-chg
 │    └── status
 │
 ├── user → **Utilization** → **_What am I using ?_**
 │    ├── get
 │    │
 │    ├── devices
 │    │     ├── list
 │    │     ├── get --id <device_id>
 │    │     ├── add --file <file_path>
 │    │     └── delete --id <device_id>
 │    │
 │    ├── leases
 │    │     ├── list
 │    │     ├── get --id <lease_id>
 │    │     ├── create --file <file_path>
 │    │     └── revoke --id <lease_id>
 │    │
 │    └── profiles
 │          ├── list
 │          └── get --id <profile_id>
 │
 ├── global-config → **Configuration** → **_How does the instance work ?_**
 │    ├── get [--output <file_path> | none]
 │    ├── diff --file <file_path> [--colored-diff | none]
 │    ├── validate --file <file_path>
 │    └── apply --file <file_path> [--dry-run | none]
 │
 └── admin → **Administration** → **_Who has what rights / What is the administered state ?_**
      │
      ├── users
      │     ├── list [--device <device_id> &/| --lease <lease_id> &/| --profile <profile_id> | none]
      │     ├── get --user <user_id>
      │     ├── create --file <file_path>
      │     ├── update --user <user_id> --file <file_path>
      │     ├── delete --user <user_id>
      │     ├── assign --user <user_id> --profile <profile_id>
      │     └── unassign --user <user_id> --profile <profile_id>
      │
      ├── devices
      │     ├── list [--lease <lease_id> | --profile <profile_id> | none]
      │     ├── get --device <device_id>
      │     ├── update --device <device_id> --file <file_path>
      │     ├── block --device <device_id>
      │     └── delete --device <device_id>
      │
      ├── leases
      │     ├── list [
      │     │         --user <user_id>
      │     │     &/| --device <device_id>
      │     │     &/| --profile <profile_id>
      │     │     &/| --status <status>
      │     │     | none
      │     │     ]
      │     ├── get --lease <lease_id>
      │     └── revoke --lease <lease_id>
      │
      └── profiles
            ├── list [--user <user_id> &/| --device <device_id> &/| --lease <lease_id> | none]
            ├── get --profile <profile_id> [--json | --yaml | none]
            ├── create --file <file_path>
            ├── update --profile <profile_id> --file <file_path>
            └── delete --profile <profile_id>
```

### Admin user files

`ttlama admin users create --file` and `update --user <user_id> --file` accept UTF-8 JSON or YAML objects. Create files require `username`; `email`, `enabled`, `is_admin`, and `password` are optional. Update files contain only the fields to change; use `email: null` to clear the email address. A password in the input file is sent to the API but is never displayed by the CLI. If no password is supplied and the server uses internal authentication, the API generates one and the CLI displays it in the creation response only; save it immediately because it cannot be retrieved later. Without internal authentication, no internal credential is created when the password is omitted.

The JSON or YAML output of `ttlama admin users get <user_id> --json` or `--yaml` is a flat object containing the editable fields returned by the API and can be passed directly to `update --user <user_id> --file`. List output remains a collection and is not an update body. Passwords are never returned; add a `password` field manually when changing one.

### Admin profile files

`ttlama admin profiles create --file` accepts a UTF-8 JSON or YAML object with `name`, `default_duration`, `maximum_duration`, and a non-empty `networks` list of CIDRs. Durations use `d`, `h`, `m`, or `s` units, and the default cannot exceed the maximum. For example:

```yaml
name: office-access
default_duration: 1h
maximum_duration: 8h
networks:
      - 10.0.0.0/24
```

`update --profile <profile_id> --file` accepts any subset of those fields. `get --profile <profile_id> --json` and `--yaml` output a flat object that can be passed to `update --file`; `list` filters `--user`, `--device`, and `--lease` are combined with AND. Historical profiles without a policy return only their name, so add the complete policy fields before updating one. Deleting a profile revokes it and its dependent assignments and leases.
