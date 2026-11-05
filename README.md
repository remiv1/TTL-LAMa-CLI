# TTL-LAMa CLI

English | [Français](https://github.com/remiv1/TTL-LAMa-CLI/blob/main/docs/README.fr.md)

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Typer](https://img.shields.io/badge/CLI-Typer-009688)](https://typer.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/remiv1/TTL-LAMa-CLI/blob/main/LICENSE)
![Coverage](https://img.shields.io/badge/Coverage-77%25-yellow)

[![Logo](https://github.com/remiv1/TTL-LAMa/blob/main/docs/img/logo_300ppp.png)](https://github.com/remiv1/TTL-LAMa/blob/main/docs/img/logo_300ppp.png)

`ttlama` is the command-line interface for TTL-LAMa (Time-to-Live Lease Administration Manager). It lets users and administrators interact with a TTL-LAMa instance through its HTTP API, without relying on the web interface.

The CLI lives in the `cli/` directory and can evolve independently of the server. TTL-LAMa manages temporary network access as leases; the CLI is neither a VPN client nor a general-purpose network administration tool.

## Project status

The CLI is under development. Currently available commands let you configure the server address, authenticate with an internal account, check and close the current session, change the signed-in user's password, inspect their overview, profiles, devices, and leases, and manage users, devices, leases, and profiles. Commands marked as planned below are targets for future implementation, not commands that can be used today.

| Group | Available commands | Planned commands |
| --- | --- | --- |
| `config` | `set-server` | — |
| `auth` | `login internal`, `login oidc`, `logout`, `password-chg`, `status` | — |
| `user` | `get`, `profiles ls`, `profiles get`, `devices ls/get/add/delete`, `leases ls/get/create/revoke` | — |
| `global-config` | `get`, `diff`, `validate`, `apply` | — |
| `admin users` | `ls`, `get`, `create`, `update`, `delete`, `assign`, `unassign` | — |
| `admin devices` | `ls`, `get`, `update`, `block`, `delete` | — |
| `admin leases` | `ls`, `get`, `revoke` | — |
| `admin profiles` | `ls`, `get`, `create`, `update`, `delete` | — |

Remaining planned commands will cover the resources and operations exposed by the [v1 API](https://github.com/remiv1/TTL-LAMa/blob/main/src/api/v1/README.md) (see the github.com/remiv1/TTL-LAMa repository). Their filtering options and file formats will be defined as they are implemented.

Administrators can list leases using any combination of `--user`, `--device`, `--profile`, and `--status` (`active`, `expired`, or `revoked`). `get` displays the complete lease, including its derived status and lifecycle timestamps. `revoke` asks for confirmation before revoking the lease; its history is retained.

```bash
ttlama admin leases ls --status active --yaml
ttlama admin leases get --lease 73 --json
ttlama admin leases revoke --lease 73
```

### Global configuration

`ttlama global-config get` reads the server's application YAML document;
`--json` and `--yaml` emit the raw document structure. Direct secret values are
shown as `[REDACTED]`. `diff --file` compares a local JSON or YAML candidate
with the current file, compares redacted secrets on the server, and never prints
direct secret values; `--check-all` also lists unchanged values.
`validate --file` asks the server to validate a candidate without writing it.
`apply --file` displays the changes and asks for confirmation; `--dry-run`
validates and displays the diff without applying it.

This group writes only the application configuration file selected by the
server's `TTL_LAMA_CONFIG_FILE` setting. It does not manage profile definitions,
`backend_config.yml`, or profile policies in the database. Replace masked
secrets with values or secret-file references before applying. Environment
variables continue to override YAML settings. Applying a file requires an
external server restart, and the CLI warns when the target is not covered by a
volume mount because the change may be lost when the container is replaced.

```bash
ttlama global-config get --yaml
ttlama global-config diff --file config.yml --check-all
ttlama global-config validate --file config.yml
ttlama global-config apply --file config.yml --dry-run
```

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

Sign in with the configured OIDC provider. By default, the CLI opens a browser and listens for a short-lived callback on `127.0.0.1`; `--distant` instead displays a verification URL and user code for approval in another browser. The OIDC client secret stays on the server, and the CLI stores the Bearer token only after successful approval without displaying it.

```bash
ttlama auth login oidc
ttlama auth login oidc --distant
```

The distant flow requires the provider's discovery document to publish `device_authorization_endpoint` and support the `urn:ietf:params:oauth:grant-type:device_code` grant for the configured client.

Change the password of the signed-in account. The current password and the new password are prompted for securely, with a second prompt to confirm the new password. After success, all of the account's sessions are revoked, including the CLI token; sign in again to store a new token.

```bash
ttlama auth password-chg
```

Inspect the current session, including active session expirations, or close the session used by this CLI instance:

```bash
ttlama auth status
ttlama auth status --json
ttlama auth status --yaml
ttlama auth status --check
ttlama auth logout
```

`status` does not display access tokens or their hashes. With no locally stored token it reports a disconnected state and exits successfully; use `--check` to return a nonzero exit code instead. `logout` revokes only the current CLI session. It removes the local token after success, and also cleans up a token the server reports as invalid; a server/network error keeps the token so the operation can be retried. JSON and YAML status output contain `session` (`active` or `inactive`), `user` (`null` without a local token; otherwise `id`, `username`, `email`, and `is_admin`), and `sessions`, a list of `expires_at` timestamps.

## Configuration and credentials

The instance address and port are stored in `config.json` under the user configuration directory determined by `platformdirs` (for example, the XDG directory on Linux). The URL must use `http` or `https` and must not contain credentials, query parameters, or a fragment.

The access token is stored in the system keyring through `keyring`, in one entry per configured instance. It is not written to the JSON configuration file. A password change revokes this token on the server; the next successful login replaces the local token.

## Code layout

- `src/ttlama_cli/cli.py` defines the `ttlama` command and its groups.
- `src/ttlama_cli/commands/` contains the Typer commands, including `auth`, `config`, `admin`, and `user`.
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
 │    │     └── oidc [--distant | none]
 │    │
 │    ├── logout
 │    ├── password-chg
 │    └── status [--json | --yaml | none] [--check | none]
 │
 ├── user → **Utilization** → **_What am I using ?_**
 │    ├── get
 │    │
 │    ├── devices
 │    │     ├── ls
 │    │     ├── get --id <device_id>
 │    │     ├── add --file <file_path>
 │    │     └── delete --id <device_id>
 │    │
 │    ├── leases
 │    │     ├── ls
 │    │     ├── get --id <lease_id>
 │    │     ├── create --file <file_path>
 │    │     └── revoke --id <lease_id>
 │    │
 │    └── profiles
 │          ├── ls
 │          └── get --id <profile_id>
 │
 ├── global-config → **Configuration** → **_How does the instance work ?_**
 │    ├── get [--json | none] [--yaml | none]
 │    ├── diff --file <file_path> [--check-all | none]
 │    ├── validate --file <file_path>
 │    └── apply --file <file_path> [--dry-run | none]
 │
 ├── admin → **Administration** → **_Who has what rights / What is the administered state ?_**
 │    │
 │    ├── users
 │    │     ├── ls [--device <id> | none ] [--lease <id> | none ] [--profile <id> | none]
 │    │     ├── get --user <user_id>
 │    │     ├── create --file <file_path>
 │    │     ├── update --user <user_id> --file <file_path>
 │    │     ├── delete --user <user_id>
 │    │     ├── assign --user <user_id> --profile <profile_id>
 │    │     └── unassign --user <user_id> --profile <profile_id>
 │    │
 │    ├── devices
 │    │     ├── ls [--lease <id> | none ] [--profile <id> | none]
 │    │     ├── get --device <device_id>
 │    │     ├── update --device <device_id> --file <file_path>
 │    │     ├── block --device <device_id>
 │    │     └── delete --device <device_id>
 │    │
 │    ├── leases
 │    │     ├── ls [--user <id> | none ] [--device <id> | none ] [--profile <id> | none ] [--status <status> | none]
 │    │     ├── get --lease <lease_id>
 │    │     └── revoke --lease <lease_id>
 │    │
 │    └── profiles
 │          ├── ls [--user <id> &/| --device <id> &/| --lease <id> | none]
 │          ├── get --profile <profile_id> [--json | --yaml | none]
 │          ├── create --file <file_path>
 │          ├── update --profile <profile_id> --file <file_path>
 │          └── delete --profile <profile_id>
 │
 └── backend → **Backend** → **_Server-side operations and configurations_**
      │
      ├── wg
      │     └── leases
      │           ├── ls [--device <id> | none ]
      │           ├── get --lease <lease_id>
      │           ├── apply --file <file_path>
      │           └── delete --lease <lease_id>
      │
      ├── openvpn
      │     └── ...
      │
      └── ...
```

Retrieve the complete CLI command documentation in [cli-reference.md](https://github.com/remiv1/TTL-LAMa-CLI/blob/main/docs/cli-reference.md).

### Input file examples

Ready-to-use JSON and YAML examples for every `--file` command are available in [docs/examples/](https://github.com/remiv1/TTL-LAMa-CLI/blob/main/docs/examples/): users (`users/user-create`, `users/user-update`), profiles (`profiles/profile-create`, `profiles/profile-update`), devices (`devices/device-add`, `devices/device-update`), and leases (`leases/lease-create`).

### Admin user files

`ttlama admin users create --file` and `update --user <user_id> --file` accept UTF-8 JSON or YAML objects. Create files require `username`; `email`, `enabled`, `is_admin`, and `password` are optional. Update files contain only the fields to change; use `email: null` to clear the email address. A password in the input file is sent to the API but is never displayed by the CLI. If no password is supplied and the server uses internal authentication, the API generates one and the CLI displays it in the creation response only; save it immediately because it cannot be retrieved later. Without internal authentication, no internal credential is created when the password is omitted.

Create files may also include `oidc_links`, a list of identities identified by `issuer` and `subject`. Update files use `link_oidc` to add identities and `unlink_oidc` to remove them. Both values must exactly match the issuer and `sub` supplied by the OIDC provider; identities are not matched by email. An identity already linked to another account causes a conflict. Repeating a link or unlink operation has no additional effect. The CLI warns when unlinking because removing the last identity prevents future OIDC sign-in for that account.

The JSON or YAML output of `ttlama admin users get <user_id> --json` or `--yaml` is a flat object containing the editable fields returned by the API and can be passed directly to `update --user <user_id> --file`. List output remains a collection and is not an update body. Passwords are never returned; add a `password` field manually when changing one.

`ttlama admin users assign --user <user_id> --profile <profile_id>` assigns a
profile to a user; repeating the command is idempotent. The matching
`unassign` command revokes the active assignment and its associated leases.

### Admin device files

`ttlama admin devices update --device <device_id> --file` accepts a UTF-8 JSON or YAML object with one or both of `name` and `public_key`. Device ownership and lifecycle fields cannot be changed. The JSON or YAML output of `ttlama admin devices get --device <device_id> --json` or `--yaml` contains only those editable fields and can be passed directly to `update --file`. The default console view shows the complete device record; the list table omits public keys, while structured list output contains the full API records. The `ls` filters `--lease` and `--profile` can be combined.

Both `block` and `delete` ask for confirmation and revoke the device's active leases. `block` marks the device as blocked; `delete` is a logical deletion that retains the device history.

### Admin profile files

`ttlama admin profiles create --file` accepts a UTF-8 JSON or YAML object with `name`, `default_duration`, `maximum_duration`, and a non-empty `networks` list of CIDRs. Durations use `d`, `h`, `m`, or `s` units, and the default cannot exceed the maximum. For example:

```yaml
name: office-access
default_duration: 1h
maximum_duration: 8h
networks:
      - 10.0.0.0/24
```

`update --profile <profile_id> --file` accepts any subset of those fields. `get --profile <profile_id> --json` and `--yaml` output a flat object that can be passed to `update --file`; `ls` filters `--user`, `--device`, and `--lease` are combined with AND. Historical profiles without a policy return only their name, so add the complete policy fields before updating one. Deleting a profile requires typing its full name, then revokes it and its dependent assignments and leases.
