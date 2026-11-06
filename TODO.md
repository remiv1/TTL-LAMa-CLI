# TODO

## Distribution and privileged invocation

- [ ] Choose and document the supported installation source (published package or built artifact) and provide a reproducible install/update procedure.
- [x] Provide a stable, root-owned installation and command path for administrative use; do not rely on a per-user virtual environment or a symlink to a user-writable executable.
- [ ] Document the behavior of `sudo ttlama`, including its separate home directory, configuration and credential store; define which operations, if any, require elevated privileges.
- [x] Keep configuration values separate from credentials; document the supported configuration files and secret-storage mechanism.

## WireGuard backend CLI

The CLI currently provides one-shot local `backend wg leases` commands. Periodic reconciliation belongs to the application scheduler and is tracked in the root [TODO](../TODO.md); a CLI-owned systemd service is out of scope.

- [ ] Document the trust boundary and safe use of local WireGuard mutation commands.
- [ ] Align `docs/cli-reference.md` and both CLI READMEs with the actual help output, including `--version`, `backend`, and option-based arguments.
- [ ] Reconcile the installation instructions with the package metadata and actual release source, including the `/opt/ttl-lama-cli/bin/ttlama` path expected by the root installer.
- [x] Resolve the README license-badge mismatch against the Apache-2.0 package license.
