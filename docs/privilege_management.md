# Backend Privilege Management

TTL-LAMa is designed to operate without direct privileged access to the host's network infrastructure.

Operations that require system privileges are executed on the server hosting the VPN backend through a dedicated SSH connection.

This separation keeps the TTL-LAMa container unprivileged while granting the backend only the permissions strictly required to materialize and revoke leases.

## Architecture

The general model is as follows:

```text
TTL-LAMa container
│
├── API
├── scheduler
└── backend
     │
     │ SSH
     ▼
VPN server
│
├── dedicated system user: <ssh_config.user>
│
├── TTL-LAMa CLI
│    │
│    └── `ttlama backend <backend>` ...
│
└── controlled privilege escalation
     │
     ▼
VPN manager
```

For WireGuard:

```text
TTL-LAMa
   │
   │ SSH
   ▼
`ttlama` user
   │
   ▼
sudo -n ttlama backend wg leases ...
   │
   ▼
WireGuardDriver
   │
   ▼
  wg
   │
   ▼
wg0
```

The SSH connection is the boundary between the TTL-LAMa application and the VPN server.

## Installing the CLI on the VPN Server

The `ttlama` CLI must be installed globally on the VPN server and managed by the operator.

Neither the executable nor its corresponding Python code must be modifiable by the dedicated SSH user.

The installation must provide a stable command, for example:

```bash
/usr/local/bin/ttlama backend <backend> ...
```

The dedicated user must be able to run `ttlama --help` normally without having administrative privileges.

From the root of the CLI repository:

```bash
mkdir -p /opt/ttlama-cli
cd /opt/ttlama-cli
sudo python3 -m venv /opt/ttlama-cli
sudo ./bin/python -m pip install --upgrade pip
sudo ./bin/python -m pip install ttlama-cli
sudo ln -sfn /opt/ttlama-cli/bin/ttlama /usr/local/bin/ttlama
/usr/local/bin/ttlama --help
```

## Dedicated System User

A dedicated system user must be created on the server hosting the backend.

```bash
sudo useradd \
  --system \
  --create-home \
  --home-dir /var/lib/ttlama \
  --shell /bin/bash \
  <ssh_config.user>
```

This user:

- Is not root.
- Is reserved for operations performed by TTL-LAMa.
- Has a dedicated SSH key.
- Must not have general administrative privileges.
- Receives only the permissions required by the configured backend.

Its home directory may contain, for example:

```text
/var/lib/ttlama/
└── .ssh/
    └── authorized_keys
```

## Privilege Management with `sudo`

Some driver operations require system privileges. WireGuard, in particular, requires appropriate permissions to modify the interface state.

Two modes of operation are distinguished.

### Manual Administration

An administrator can explicitly run the CLI with `sudo`:

```bash
sudo ttlama backend wg leases ...
```

This mode is primarily intended for diagnostics, tests, and occasional administrative operations.

### Automated Execution

For calls originating from the TTL-LAMa application, the user specified in the configuration remains unprivileged. Only the `ttlama backend` commands required by the configured backend should be allowed to run with controlled elevation.

The `sudoers` configuration must follow the principle of least privilege. In particular, it must not grant the configured user a general authorization such as:

```text
Cmnd_Alias TTLAMA_BACKEND = /usr/local/bin/ttlama backend *
ttlama ALL=(root) NOPASSWD: TTLAMA_BACKEND
```

Permissions must be limited to the operations required by the backend. A dedicated configuration can be placed in `/etc/sudoers.d/ttlama`. Validate it with:

```bash
sudo visudo -cf /etc/sudoers.d/ttlama
```

The remote application invokes the backend CLI with `sudo -n`. Privilege escalation applies to the `ttlama backend ...` command; the driver selected by the CLI then runs in that context and does not invoke `sudo` itself. Any password prompt must be treated as a backend configuration error.

## SSH Configuration

The settings TTL-LAMa uses to reach the VPN server are stored in a dedicated configuration file at `/etc/ttl-lama/ssh_config.yml`.

Example configuration:

```yaml
ssh_config:
  host: host.containers.internal # or vpn.example.com
  port: 22
  user: ttlama

  identity_file: /run/secrets/ttlama_ssh_key
  known_hosts_file: /etc/ttl-lama/ssh_known_hosts

  connection_timeout: 10
```

This file describes the SSH transport. It does not contain the private key itself.
The scheduler reads it when opening an SSH connection; the connection values are not stored in the application configuration.

The backend configuration remains separate, in `/etc/ttl-lama/backend_config.yml`:

```yaml
backend:
  wireguard:
    interfaces:
      - name: wg0
        description: Main WireGuard interface
        networks:
          - 10.0.0.1/24
        public_key: your_public_key_here
        default_duration: 8h
        maximum_duration: 24h
```

This separation distinguishes:

- `ssh_config.yml`: **_How should the host be reached?_**
- `backend_config.yml`: **_Which infrastructure should be managed?_**

### Dedicated SSH Key

TTL-LAMa uses a dedicated SSH key pair to communicate with the VPN server.

The key pair must not be reused for human administration of the server. It can be generated with:

```bash
ssh-keygen \
  -t ed25519 \\
  -f ttlama_backend \\
  -C "TTL-LAMa backend"
```

Two files are generated:

- `ttlama_backend`: The private key TTL-LAMa uses to connect to the server.
- `ttlama_backend.pub`: The corresponding public key to install on the VPN server.

#### Private Key

The private key belongs on the TTL-LAMa application side. It must never:

- Be built into the container image.
- Be committed to the Git repository.
- Be copied to the VPN server.
- Appear in logs.

It must be injected at deployment time through the operator's secret management mechanism. The file configured in `ssh_config.yml` specifies its location:

```yaml
ssh_config:
  identity_file: /run/secrets/ttlama_ssh_key
```

#### Public Key

The public key is installed on the VPN server in the dedicated account's `authorized_keys` file: `/var/lib/ttlama/.ssh/authorized_keys`.

It can be associated with SSH restrictions to reduce the capabilities available to the automated connection. In particular, the connection used by TTL-LAMa must not become a general-purpose way to administer the server.

### Verifying the Server's Identity

TTL-LAMa must verify the identity of the SSH server.

The configuration references a `known_hosts` file for this purpose:

```yaml
ssh_config:
  known_hosts_file: /etc/ttl-lama/ssh_known_hosts
```

The application must not disable server identity verification to simplify deployment. The expected host key must be provisioned by the operator.

### Separating Secrets from Configuration

Configuration and secrets have different lifecycles. The recommended layout is conceptually:

```text
/etc/ttl-lama/
├── config.yml
├── ssh_config.yml
└── ssh_known_hosts

/run/secrets/
└── ttlama_ssh_key
```

The first directory contains configuration provisioned by the operator. The second contains secrets injected at deployment time.

### Recommended Permissions

Sensitive data must have restrictive permissions.

```text
/run/secrets/ttlama_ssh_key
    read: TTL-LAMa user only

/etc/ttl-lama/ssh_known_hosts
    read: TTL-LAMa
    write: administrator only

/var/lib/ttlama/.ssh/authorized_keys
    read/write: appropriately restricted server account
```

Exact permissions should be adapted to the deployment model and the operator's secret management mechanism.

## Security Model

The intended privilege chain is:

```text
TTL-LAMa application (unprivileged)
      │
      │ dedicated SSH key
      ▼
`ttlama` account (unprivileged)
      │
      │ restricted `sudo`
      ▼
ttlama backend <backend> ...
      │
      ▼
  VPN driver
      │
      ▼
VPN infrastructure
```

A compromise at one level should not automatically grant access to the entire next level. In particular:

- The TTL-LAMa container does not receive network privileges on the host.
- The SSH key is not a human administration key.
- The SSH user is not `root`.
- `sudo` does not authorize general administrative commands.
