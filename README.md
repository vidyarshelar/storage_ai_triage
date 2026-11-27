# Storage AI Triage

A Python-based storage QA toolkit for running write, integrity, replication, and diagnostic checks against a Rocky Linux virtual machine over SSH.

## Overview

The project performs the following operations:

1. Writes a 50 MiB file to `/mnt/primary/testfile`.
2. Creates a 10 MiB random integrity file at `/mnt/primary/integrity.bin`.
3. Generates `/mnt/primary/integrity.sha256`.
4. Replicates `/mnt/primary/` to `/mnt/secondary/` with `rsync`.
5. Deliberately overwrites `/mnt/secondary/integrity.bin` with `dddd`.
6. Compares the primary and secondary SHA-256 hashes.
7. Provides mount, disk usage, block-device, file, and kernel-log diagnostics.

The intentional secondary-file corruption makes the final checksum check fail in a controlled way. This is expected fault-injection behavior; it demonstrates that mismatches are detected.

## Warning

The test modifies remote storage. It overwrites:

- `/mnt/primary/testfile`
- `/mnt/primary/integrity.bin`
- `/mnt/primary/integrity.sha256`
- `/mnt/secondary/integrity.bin`
- Files replicated from `/mnt/primary/` into `/mnt/secondary/`

Run it only on a test VM or another environment where these paths and files can be safely modified. The scripts do not clean up the intentionally corrupted secondary file.

## Requirements

### Local host

- Windows, Linux, or macOS
- Python 3.10 or later
- Network access to the target VM
- SSH access to the target VM

### Remote VM

- Rocky Linux or a compatible Linux distribution
- SSH server
- `root` or a user with permission to write both mount points
- Mounted storage at:
  - `/mnt/primary`
  - `/mnt/secondary`
- Remote utilities: `dd`, `head`, `sha256sum`, `rsync`, `df`, `mount`, `lsblk`, `ls`, and `dmesg`

## Installation

Clone the repository and install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

On Windows, use `py` instead of `python` if `python` is not on `PATH`:

```powershell
py -m pip install -r requirements.txt
```

## Configuration

Before running the scripts, configure the SSH constants in `ssh_client.py`:

```python
HOST = "127.0.0.1"
PORT = 2222
USERNAME = "root"
PASSWORD = "your-password"
```

Recommended repository practice:

- Do not commit real passwords or private keys.
- Prefer SSH key authentication for non-demo use.
- Restrict access to the test VM and storage mounts.
- Replace the hardcoded credentials with environment variables or a secrets configuration for production use.

## Preflight Checklist

Before each run:

1. Confirm SSH connectivity.
2. Confirm both mount points exist and are mounted.
3. Confirm sufficient available capacity.
4. Confirm the target environment permits the intentional file writes and fault injection.

A read-only preflight can be run through the SSH client:

```bash
python -c "from ssh_client import run_command; print(run_command('uname -a'))"
```

## Running the Tests

Compile-check the Python files:

```bash
python -m py_compile ssh_client.py storage_tools.py test_storage_io.py
```

Run the basic SSH connectivity script:

```bash
python ssh_client.py
```

Run the storage test:

```bash
python test_storage_io.py
```

Expected successful setup and write steps print messages similar to:

```text
Write test to primary storage successful.
Data integrity test successful:
Resync successful:
Secondary storage modified successfully:
Checking SHA-256 checksums for primary and secondary storage...
```

The final result should normally end with:

```text
HASH MISMATCH - TEST FAILED: primary=<primary-hash>, secondary=<secondary-hash>
AssertionError: HASH MISMATCH - TEST FAILED
```

This is the intended fault-injection result. The test process exit code is expected to be `1`.

## Diagnostics

The diagnostic functions are in `storage_tools.py`:

- `check_mount_points()` — verifies mount entries
- `check_disk_space()` — reports filesystem type and capacity
- `check_block_devices()` — reports block devices and filesystems
- `inspect_storage_files()` — lists primary and secondary storage files
- `get_kernel_logs()` — returns the final 30 kernel messages

Example:

```python
import storage_tools

print(storage_tools.check_mount_points())
print(storage_tools.check_disk_space())
print(storage_tools.check_block_devices())
print(storage_tools.inspect_storage_files())
print(storage_tools.get_kernel_logs())
```

You can also verify the live checksums directly:

```bash
sha256sum /mnt/primary/integrity.bin /mnt/secondary/integrity.bin
cat /mnt/primary/integrity.sha256
```

## Reports

Run reports use the naming convention:

```text
storage-test-report-YYYY-MM-DD.md
storage-test-report-YYYY-MM-DD-HHMM.md
```

Existing reports are included for example/diagnostic purposes. When publishing reports, remove host names, IP addresses, usernames, credentials, UUIDs, or other environment details that should not be public.

## Interpreting Results

| Outcome | Meaning |
|---|---|
| Write step succeeded | The primary mount accepted a 50 MiB write |
| Integrity step succeeded | The primary integrity file and manifest were generated |
| Replication step succeeded | `rsync` copied primary files to secondary storage |
| Secondary fault injection succeeded | The secondary integrity file was deliberately changed |
| Hash mismatch detected | The final integrity assertion behaved as designed |
| Test exit code `1` | One of the test assertions or setup steps failed; in a normal fault-injection run it means the mismatch assertion was reached |

Do not report the entire run as passed solely because a mismatch was detected. A pass interpretation requires all earlier write, integrity, and replication steps to succeed.

## Project Files

- `ssh_client.py` — Paramiko SSH connection and command execution helpers
- `test_storage_io.py` — storage write, integrity, replication, and mismatch tests
- `storage_tools.py` — mount, disk, block-device, file, and kernel diagnostics
- `requirements.txt` — Python dependencies
- `storage-test-report-*.md` — dated run reports

## Troubleshooting

### SSH connection fails

- Verify the VM IP address and forwarded SSH port.
- Confirm SSH is listening on the target VM.
- Confirm the credentials or key have access.
- Check that a host firewall or security group permits SSH.

### Mount preflight fails

- Verify `/mnt/primary` and `/mnt/secondary` exist.
- Verify both are mounted.
- Confirm they are not read-only or full.

### Replication fails

- Confirm `rsync` is installed on the VM.
- Confirm the SSH user has write permission on `/mnt/secondary`.
- Review stderr returned by `rsync`.

### Kernel diagnostics are unclear

- Compare remote UTC/local timestamps with the test run time.
- Collect a larger or run-scoped kernel/journal window when investigating storage failures.
- Avoid attributing unrelated earlier journal or watchdog events to the current test run.

## Cleanup

Cleanup is intentionally not automatic. Remove test files or restore storage only if the environment owner authorizes it:

```bash
rm -f /mnt/primary/testfile /mnt/primary/integrity.bin /mnt/primary/integrity.sha256
rm -f /mnt/secondary/testfile /mnt/secondary/integrity.bin /mnt/secondary/integrity.sha256
```

## License

Add the project license here before public distribution.
