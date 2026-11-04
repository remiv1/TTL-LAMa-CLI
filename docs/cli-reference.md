# `ttlama`

CLI to administrate TTL-LAMa.

**Usage**:

$ ttlama [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `auth`: Authentication to a TTL-LAMa.
* `config`: Configuration commands for TTL-LAMa CLI.
* `global-config`: Read and manage the application...
* `admin`: Admin commands for the TTL-LAMa CLI.
* `user`: Commands for the authenticated TTL-LAMa user.

## `ttlama auth`

Authentication to a TTL-LAMa.

**Usage**:

$ ttlama auth [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `logout`: Revoke the current session and remove its...
* `status`: Display the current identity and active...
* `password-chg`: Change the password of the authenticated...
* `login`: Login to TTL-LAMa.

### `ttlama auth logout`

Revoke the current session and remove its local token.

**Usage**:

$ ttlama auth logout [OPTIONS]

**Options**:

* `--help`: Show this message and exit.

### `ttlama auth status`

Display the current identity and active session expirations.

**Usage**:

$ ttlama auth status [OPTIONS]

**Options**:

* `--json`: Output status as JSON.
* `--yaml`: Output status as YAML.
* `--check-connected`: Exit with status 1 when no active session is available.
* `--help`: Show this message and exit.

### `ttlama auth password-chg`

Change the password of the authenticated account.

**Usage**:

$ ttlama auth password-chg [OPTIONS]

**Options**:

* `--help`: Show this message and exit.

### `ttlama auth login`

Login to TTL-LAMa.

**Usage**:

$ ttlama auth login [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `internal`: Connect with an internal account to a...
* `oidc`: Sign in with the configured OIDC provider.

#### `ttlama auth login internal`

Connect with an internal account to a TTL-LAMa session.

**Usage**:

$ ttlama auth login internal [OPTIONS]

**Options**:

* `--user <str>`: Username for internal login.  [required]
* `--help`: Show this message and exit.

#### `ttlama auth login oidc`

Sign in with the configured OIDC provider.

**Usage**:

$ ttlama auth login oidc [OPTIONS]

**Options**:

* `--distant`: Use a device code for sign-in from another browser or device.
* `--help`: Show this message and exit.

## `ttlama config`

Configuration commands for TTL-LAMa CLI.

**Usage**:

$ ttlama config [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `set-server`: Configure the server for TTL-LAMa CLI.

### `ttlama config set-server`

Configure the server for TTL-LAMa CLI.

:param url: Server URL for TTL-LAMa CLI configuration.
:type url: str
:param port: Server port for TTL-LAMa CLI configuration.
:type port: int

**Usage**:

$ ttlama config set-server [OPTIONS] {url}

**Arguments**:

* `url`: Server URL for TTL-LAMa CLI configuration.  [required]

**Options**:

* `--port <int>`: Server port for TTL-LAMa CLI configuration.  [default: 8080]
* `--help`: Show this message and exit.

## `ttlama global-config`

Read and manage the application configuration.

**Usage**:

$ ttlama global-config [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `get`: Read and display the server&#x27;s current...
* `diff`: Compare a candidate file with the server...
* `validate`: Validate a candidate configuration file on...
* `apply`: Validate, show, and optionally persist a...

### `ttlama global-config get`

Read and display the server&#x27;s current application configuration.

**Usage**:

$ ttlama global-config get [OPTIONS]

**Options**:

* `--json`: Output the configuration as JSON.
* `--yaml`: Output the configuration as YAML.
* `--help`: Show this message and exit.

### `ttlama global-config diff`

Compare a candidate file with the server configuration.

**Usage**:

$ ttlama global-config diff [OPTIONS]

**Options**:

* `--file <path>`: [required]
* `--check-all`: Include unchanged values.
* `--help`: Show this message and exit.

### `ttlama global-config validate`

Validate a candidate configuration file on the server.

**Usage**:

$ ttlama global-config validate [OPTIONS]

**Options**:

* `--file <path>`: [required]
* `--help`: Show this message and exit.

### `ttlama global-config apply`

Validate, show, and optionally persist a candidate configuration.

**Usage**:

$ ttlama global-config apply [OPTIONS]

**Options**:

* `--file <path>`: [required]
* `--dry-run`: Validate and show changes only.
* `--help`: Show this message and exit.

## `ttlama admin`

Admin commands for the TTL-LAMa CLI.

**Usage**:

$ ttlama admin [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `users`: User management commands for the TTL-LAMa...
* `devices`: Device management commands for the...
* `leases`: Lease management commands for the TTL-LAMa...
* `profiles`: Profile management commands for the...

### `ttlama admin users`

User management commands for the TTL-LAMa CLI.

**Usage**:

$ ttlama admin users [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ls`: Manage users in the TTL-LAMa CLI.
* `create`: Create a user from a JSON or YAML file.
* `update`: Update a user from a JSON or YAML file.
* `delete`: Delete a user by ID.
* `assign`: Assign a profile to a user.
* `unassign`: Revoke a profile assignment from a user.
* `get`: Get a specific user in the TTL-LAMa CLI.

#### `ttlama admin users ls`

Manage users in the TTL-LAMa CLI.

:param device: Filter by device ID.
:type device: int | None
:param lease: Filter by lease ID.
:type lease: int | None
:param profile: Filter by profile ID.
:type profile: int | None
:param json_output: Whether to output the list of users in JSON format.
:type json_output: bool
:param yaml_output: Whether to output the list of users in YAML format.
:type yaml_output: bool

**Usage**:

$ ttlama admin users ls [OPTIONS]

**Options**:

* `--device <int>`: Specify the device to list users from.
* `--lease <int>`: Specify the lease to list users from.
* `--profile <int>`: Specify the profile to list users from.
* `--json`: Output the list of users in JSON format.
* `--yaml`: Output the list of users in YAML format.
* `--help`: Show this message and exit.

#### `ttlama admin users create`

Create a user from a JSON or YAML file.

:param file_path: Path to a JSON or YAML file containing user data.
:type file_path: Path

**Usage**:

$ ttlama admin users create [OPTIONS]

**Options**:

* `--file <path>`: Path to a JSON or YAML file containing user data.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin users update`

Update a user from a JSON or YAML file.

:param user_id: The ID of the user to update.
:type user_id: str
:param file_path: Path to a JSON or YAML file containing fields to update.
:type file_path: Path

**Usage**:

$ ttlama admin users update [OPTIONS]

**Options**:

* `--user <str>`: Specify the ID of the user to update.  [required]
* `--file <path>`: Path to a JSON or YAML file containing fields to update.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin users delete`

Delete a user by ID.

:param user_id: The ID of the user to delete.
:type user_id: str

.. note::
    This is a logical deletion; the user will be marked as deleted but not permanently
    removed from the database. Until then, the user record will remain in the system.

**Usage**:

$ ttlama admin users delete [OPTIONS]

**Options**:

* `--user <str>`: Specify the ID of the user to delete.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin users assign`

Assign a profile to a user.

:param user_id: The ID of the user to assign the profile to.
:type user_id: str
:param profile_id: The ID of the profile to assign.
:type profile_id: int

**Usage**:

$ ttlama admin users assign [OPTIONS]

**Options**:

* `--user <str>`: Specify the ID of the user to assign the profile to.  [required]
* `--profile <int>`: Specify the ID of the profile to assign.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin users unassign`

Revoke a profile assignment from a user.

:param user_id: The ID of the user to unassign the profile from.
:type user_id: str
:param profile_id: The ID of the profile to unassign.
:type profile_id: int

**Usage**:

$ ttlama admin users unassign [OPTIONS]

**Options**:

* `--user <str>`: Specify the ID of the user to unassign the profile from.  [required]
* `--profile <int>`: Specify the ID of the profile to unassign.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin users get`

Get a specific user in the TTL-LAMa CLI.

:param user_id: The ID of the user to retrieve.
:type user_id: str
:param json_output: Whether to output the user information in JSON format.
:type json_output: bool
:param yaml_output: Whether to output the user information in YAML format.
:type yaml_output: bool

**Usage**:

$ ttlama admin users get [OPTIONS] {user_id}

**Arguments**:

* `user_id`: Specify the ID of the user to retrieve.  [required]

**Options**:

* `--json`: Output the user information in JSON format.
* `--yaml`: Output the user information in YAML format.
* `--help`: Show this message and exit.

### `ttlama admin devices`

Device management commands for the TTL-LAMa CLI.

**Usage**:

$ ttlama admin devices [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ls`: List devices, optionally filtered by lease...
* `get`: Retrieve a device and display its details.
* `update`: Update a device from a JSON or YAML file.
* `block`: Block a device after confirmation and...
* `delete`: Logically delete a device after confirmation.

#### `ttlama admin devices ls`

List devices, optionally filtered by lease or profile.

:param lease: Filter by lease ID.
:type lease: int | None
:param profile: Filter by profile ID.
:type profile: int | None
:param json_output: Whether to output devices as JSON.
:type json_output: bool
:param yaml_output: Whether to output devices as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama admin devices ls [OPTIONS]

**Options**:

* `--lease <int>`: Filter by lease ID.
* `--profile <int>`: Filter by profile ID.
* `--json`: Output devices as JSON.
* `--yaml`: Output devices as YAML.
* `--help`: Show this message and exit.

#### `ttlama admin devices get`

Retrieve a device and display its details.

:param device_id: The ID of the device to retrieve.
:type device_id: int
:param json_output: Whether to output editable fields as JSON.
:type json_output: bool
:param yaml_output: Whether to output editable fields as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama admin devices get [OPTIONS] {device_id}

**Options**:

* `--device <int>`: Device ID to retrieve.  [required]
* `--json`: Output editable fields as JSON.
* `--yaml`: Output editable fields as YAML.
* `--help`: Show this message and exit.

#### `ttlama admin devices update`

Update a device from a JSON or YAML file.

:param device_id: The ID of the device to update.
:type device_id: int
:param file_path: The path to the device update file.
:type file_path: Path

**Usage**:

$ ttlama admin devices update [OPTIONS] {device_id}

**Options**:

* `--device <int>`: Device ID to update.  [required]
* `--file <path>`: JSON or YAML device update file.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin devices block`

Block a device after confirmation and revoke its active leases.

:param device_id: The ID of the device to block.
:type device_id: int

**Usage**:

$ ttlama admin devices block [OPTIONS]

**Options**:

* `--device <int>`: Device ID to block.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin devices delete`

Logically delete a device after confirmation.

Deletion revokes the device and its active leases but retains its history.

:param device_id: The ID of the device to delete.
:type device_id: int

**Usage**:

$ ttlama admin devices delete [OPTIONS]

**Options**:

* `--device <int>`: Device ID to delete.  [required]
* `--help`: Show this message and exit.

### `ttlama admin leases`

Lease management commands for the TTL-LAMa CLI.

**Usage**:

$ ttlama admin leases [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ls`: List leases, optionally filtered by user,...
* `get`: Retrieve a lease and display all of its...
* `revoke`: Revoke a lease after confirmation while...

#### `ttlama admin leases ls`

List leases, optionally filtered by user, device, profile, or status.

**Usage**:

$ ttlama admin leases ls [OPTIONS]

**Options**:

* `--user <str>`: Filter by user UUID.
* `--device <int>`: Filter by device ID.
* `--profile <int>`: Filter by profile ID.
* `--status <active|expired|revoked>`: Filter by status: active, expired, or revoked.
* `--json`: Output leases as JSON.
* `--yaml`: Output leases as YAML.
* `--help`: Show this message and exit.

#### `ttlama admin leases get`

Retrieve a lease and display all of its fields.

**Usage**:

$ ttlama admin leases get [OPTIONS] {lease_id}

**Options**:

* `--lease <int>`: Lease ID to retrieve.  [required]
* `--json`: Output the lease as JSON.
* `--yaml`: Output the lease as YAML.
* `--help`: Show this message and exit.

#### `ttlama admin leases revoke`

Revoke a lease after confirmation while retaining its history.

**Usage**:

$ ttlama admin leases revoke [OPTIONS] {lease_id}

**Options**:

* `--lease <int>`: Lease ID to revoke.  [required]
* `--help`: Show this message and exit.

### `ttlama admin profiles`

Profile management commands for the TTL-LAMa CLI.

**Usage**:

$ ttlama admin profiles [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ls`: List profiles, optionally filtered by...
* `get`: Retrieve a profile and display its...
* `create`: Create a profile from a JSON or YAML file.
* `update`: Update a profile from a JSON or YAML file.
* `delete`: Revoke a profile and its dependent access.

#### `ttlama admin profiles ls`

List profiles, optionally filtered by user, device, or lease.

:param user: Filter by assigned user UUID.
:type user: str | None
:param device: Filter by device ID.
:type device: int | None
:param lease: Filter by lease ID.
:type lease: int | None
:param json_output: Whether to output the profiles as JSON.
:type json_output: bool
:param yaml_output: Whether to output the profiles as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama admin profiles ls [OPTIONS]

**Options**:

* `--user <str>`: Filter by assigned user UUID.
* `--device <int>`: Filter by device ID.
* `--lease <int>`: Filter by lease ID.
* `--json`: Output profiles as JSON.
* `--yaml`: Output profiles as YAML.
* `--help`: Show this message and exit.

#### `ttlama admin profiles get`

Retrieve a profile and display its updateable fields.

:param profile_id: The ID of the profile to retrieve.
:type profile_id: int
:param json_output: Whether to output the profile as JSON.
:type json_output: bool
:param yaml_output: Whether to output the profile as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama admin profiles get [OPTIONS]

**Options**:

* `--profile <int>`: Profile ID to retrieve.  [required]
* `--json`: Output the profile as JSON.
* `--yaml`: Output the profile as YAML.
* `--help`: Show this message and exit.

#### `ttlama admin profiles create`

Create a profile from a JSON or YAML file.

:param file_path: Path to the JSON or YAML profile data file.
:type file_path: Path

**Usage**:

$ ttlama admin profiles create [OPTIONS]

**Options**:

* `--file <path>`: JSON or YAML profile data file.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin profiles update`

Update a profile from a JSON or YAML file.

:param profile_id: The ID of the profile to update.
:type profile_id: int
:param file_path: Path to the JSON or YAML fields to update.
:type file_path: Path

**Usage**:

$ ttlama admin profiles update [OPTIONS]

**Options**:

* `--profile <int>`: Profile ID to update.  [required]
* `--file <path>`: JSON or YAML fields to update.  [required]
* `--help`: Show this message and exit.

#### `ttlama admin profiles delete`

Revoke a profile and its dependent access.

:param profile_id: The ID of the profile to revoke.
:type profile_id: int

**Usage**:

$ ttlama admin profiles delete [OPTIONS]

**Options**:

* `--profile <int>`: Profile ID to revoke.  [required]
* `--help`: Show this message and exit.

## `ttlama user`

Commands for the authenticated TTL-LAMa user.

**Usage**:

$ ttlama user [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `get`: Display the current user, devices, leases,...
* `devices`: Inspect devices owned by the authenticated...
* `leases`: Inspect leases owned by the authenticated...
* `profiles`: Inspect profiles assigned to the...

### `ttlama user get`

Display the current user, devices, leases, and assigned profiles.

**Usage**:

$ ttlama user get [OPTIONS]

**Options**:

* `--json`: Output as JSON.
* `--yaml`: Output as YAML.
* `--help`: Show this message and exit.

### `ttlama user devices`

Inspect devices owned by the authenticated user.

**Usage**:

$ ttlama user devices [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ls`: List devices owned by the authenticated user.
* `get`: Retrieve an owned device by ID.
* `add`: Add a device from a JSON or YAML file.
* `delete`: Revoke an owned device and its active leases.

#### `ttlama user devices ls`

List devices owned by the authenticated user.

:param json_output: Whether to output as JSON.
:type json_output: bool
:param yaml_output: Whether to output as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama user devices ls [OPTIONS]

**Options**:

* `--json`: Output devices as JSON.
* `--yaml`: Output devices as YAML.
* `--help`: Show this message and exit.

#### `ttlama user devices get`

Retrieve an owned device by ID.

:param device_id: The ID of the device to retrieve.
:type device_id: int
:param json_output: Whether to output as JSON.
:type json_output: bool
:param yaml_output: Whether to output as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama user devices get [OPTIONS] {device_id}

**Options**:

* `--id <int>`: Device ID to retrieve.  [required]
* `--json`: Output the device as JSON.
* `--yaml`: Output the device as YAML.
* `--help`: Show this message and exit.

#### `ttlama user devices add`

Add a device from a JSON or YAML file.

:param file_path: The path to the JSON or YAML device data file.
:type file_path: Path

**Usage**:

$ ttlama user devices add [OPTIONS] {file_path}

**Options**:

* `--file <path>`: JSON or YAML device data file.  [required]
* `--help`: Show this message and exit.

#### `ttlama user devices delete`

Revoke an owned device and its active leases.

:param device_id: The ID of the device to revoke.
:type device_id: int

**Usage**:

$ ttlama user devices delete [OPTIONS] {device_id}

**Options**:

* `--id <int>`: Device ID to revoke.  [required]
* `--help`: Show this message and exit.

### `ttlama user leases`

Inspect leases owned by the authenticated user.

**Usage**:

$ ttlama user leases [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ls`: List leases owned by the authenticated user.
* `get`: Retrieve an owned lease by ID.
* `create`: Create a lease from a JSON or YAML file.
* `revoke`: Revoke an owned lease without deleting its...

#### `ttlama user leases ls`

List leases owned by the authenticated user.

:param json_output: Whether to output as JSON.
:type json_output: bool
:param yaml_output: Whether to output as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama user leases ls [OPTIONS]

**Options**:

* `--json`: Output leases as JSON.
* `--yaml`: Output leases as YAML.
* `--help`: Show this message and exit.

#### `ttlama user leases get`

Retrieve an owned lease by ID.

:param lease_id: The ID of the lease to retrieve.
:type lease_id: int
:param json_output: Whether to output as JSON.
:type json_output: bool
:param yaml_output: Whether to output as YAML.
:type yaml_output: bool

**Usage**:

$ ttlama user leases get [OPTIONS]

**Options**:

* `--id <int>`: Lease ID to retrieve.  [required]
* `--json`: Output the lease as JSON.
* `--yaml`: Output the lease as YAML.
* `--help`: Show this message and exit.

#### `ttlama user leases create`

Create a lease from a JSON or YAML file.

:param file_path: Path to the JSON or YAML lease data file.
:type file_path: Path

**Usage**:

$ ttlama user leases create [OPTIONS]

**Options**:

* `--file <path>`: JSON or YAML lease data file.  [required]
* `--help`: Show this message and exit.

#### `ttlama user leases revoke`

Revoke an owned lease without deleting its history.

:param lease_id: The ID of the lease to revoke.
:type lease_id: int

**Usage**:

$ ttlama user leases revoke [OPTIONS]

**Options**:

* `--id <int>`: Lease ID to revoke.  [required]
* `--help`: Show this message and exit.

### `ttlama user profiles`

Inspect profiles assigned to the authenticated user.

**Usage**:

$ ttlama user profiles [OPTIONS] COMMAND [ARGS]...

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ls`: List profiles actively assigned to the...
* `get`: Retrieve an assigned profile by ID.

#### `ttlama user profiles ls`

List profiles actively assigned to the current user.

**Usage**:

$ ttlama user profiles ls [OPTIONS]

**Options**:

* `--json`: Output profiles as JSON.
* `--yaml`: Output profiles as YAML.
* `--help`: Show this message and exit.

#### `ttlama user profiles get`

Retrieve an assigned profile by ID.

**Usage**:

$ ttlama user profiles get [OPTIONS]

**Options**:

* `--id <int>`: Profile ID to retrieve.  [required]
* `--json`: Output the profile as JSON.
* `--yaml`: Output the profile as YAML.
* `--help`: Show this message and exit.
