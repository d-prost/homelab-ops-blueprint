# Remote SSH proof — 2026-09-27

- Repository commit: `3303507b0efe634bfc603c39063237651cabb0f7`
- Topology: separate Linux control host and disposable SSH target
- Target OS: Ubuntu 26.04.1 LTS
- Docker Engine: 29.8.1
- Docker Compose: 5.5.1
- Control Ansible Core: 2.20.1

## Baseline deployment

- Trusted SSH host key checked before connection: PASS
- Declared target hostname checked by Ansible: PASS
- Machine ID pinning: not configured
- Immutable image preflight: PASS
- Dozzle deployment and functional HTTP check: PASS
- Durable acceptance record and receipt: PASS
- Elapsed time: 19 seconds

## Injected failure and rollback

- Fixture: disposable Dozzle candidate exits with code 42 and adds a candidate-only managed file.
- Candidate result: REJECTED
- Terminal result: `REJECTED_ROLLBACK_VERIFIED`
- Previous managed-file SHA-256 values restored: PASS
- Candidate-only managed file removed: PASS
- Previous accepted record unchanged: PASS
- Previous functional HTTP check rerun successfully: PASS
- Elapsed time: 26 seconds

## Cleanup

- Dozzle container and Compose network removed: PASS
- Project-managed target directory, record, receipt and unresolved marker absent: PASS
- Temporary passwordless sudo rule removed; noninteractive sudo requires authentication again: PASS
- Temporary control-host public key removed from target: PASS
- Control checkout and target checkout clean: PASS
- Temporary control workspace, inventory and SSH key removed: PASS
- Private inventory and SSH material committed to repository: NO

## Compatibility observations

- `collect-remote-proof-facts.sh` passes inventory, target identity and Docker preflight, then fails while reporting the Docker Engine version. Its `{{.Server.Version}}` Docker format string is interpreted as an Ansible/Jinja expression. The Docker version above was collected over verified SSH.
- The target account's default `umask 0002` makes a recovery-readiness test fixture group-writable. Local validation passed with `umask 022`.
- Ubuntu's `sudo-rs` keeps authentication per terminal. A temporary, explicitly authorized sudo rule was needed for noninteractive Ansible and was removed after testing.

Raw Ansible logs are retained locally outside the public repository. They contain private operational details and should not be published.
