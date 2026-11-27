# Storage I/O Test Diagnosis Report

**Date:** 2026-11-27
**Run time:** 14:29 local time (post-run UTC diagnostic timestamp: 09:01:31Z)
**Host under test:** Rocky Linux VM `vm1`
**Overall result:** **FAILED — test process exit code 1**. Earlier primary write, integrity generation, and replication steps succeeded. The final checksum assertion failed because deliberate fault injection changed the secondary integrity file.

## 1. Mutating action confirmation

The user confirmed the following intentional actions before execution:

- Write/overwrite `/mnt/primary/testfile`
- Write/overwrite `/mnt/primary/integrity.bin`
- Write/overwrite `/mnt/primary/integrity.sha256`
- Replicate `/mnt/primary/` to `/mnt/secondary/`
- Deliberately overwrite `/mnt/secondary/integrity.bin`
- Leave the intentionally modified files in place

## 2. Script compilation

`python -m py_compile test_storage_io.py ssh_client.py storage_tools.py`

- Exit code: **0**
- Compilation: **passed**
- No compilation stderr was produced.

## 3. SSH and preflight checks

### SSH connectivity

A read-only `uname -a` command through `ssh_client.run_command()` returned exit code 0:

`Linux vm1 6.12.0-211.16.1.el10_2.0.1.x86_64 #1 SMP PREEMPT_DYNAMIC Sun May 24 12:28:00 UTC 2026 x86_64 GNU/Linux`

### Mount preflight

- `/mnt/primary`: exists and `mountpoint -q` result reported `True` / exit code 0
- `/mnt/secondary`: exists and `mountpoint -q` result reported `True` / exit code 0

### Capacity preflight

- `/mnt/primary`: 983040 KiB size, 113372 KiB used, 869668 KiB available
- `/mnt/secondary`: 983040 KiB size, 103136 KiB used, 879904 KiB available

Preflight result: **passed**; both mounts had more than sufficient capacity for the 50 MiB and 10 MiB writes.

## 4. Process results

### `ssh_client.py`

- Exit code: **0**
- stdout: remote `ls -l` listing completed successfully
- stderr: empty

### `test_storage_io.py`

- Exit code: **1**
- stdout:
  - `Write test to primary storage successful.`
  - `Data integrity test successful.`
  - `Resync successful.`
  - `Secondary storage modified successfully.`
  - Hash mismatch assertion raised
- stderr: Python `AssertionError: HASH MISMATCH - TEST FAILED: primary=a1718d38331bde978d37b4f91a836acaf775fc74f354e90f431169da56f62017, secondary=5a4374779c218ee174d4dd904f61579f3f54cc4e62f5fe0bfe50f665e066095c`

The nonzero result is the expected deliberate fault-injection assertion, not an SSH, write, integrity-generation, or replication failure.

## 5. Test steps

| Step | Evidence | Result |
|---|---|---|
| Primary 50 MiB write | `dd` returned exit code 0 | Passed |
| Primary integrity file generation | 10 MiB file and manifest commands returned exit code 0 | Passed |
| Primary-to-secondary rsync | rsync returned exit code 0 | Passed |
| Fault injection | Secondary integrity file overwritten successfully | Passed |
| SHA-256 comparison | Primary and secondary hashes differed | Expected mismatch detected |

## 6. Exact checksum verification

Actual post-run checksums for the files themselves:

- Primary: `a1718d38331bde978d37b4f91a836acaf775fc74f354e90f431169da56f62017` `/mnt/primary/integrity.bin`
- Secondary: `5a4374779c218ee174d4dd904f61579f3f54cc4e62f5fe0bfe50f665e066095c` `/mnt/secondary/integrity.bin`

The primary manifest `/mnt/primary/integrity.sha256` contains:

`a1718d38331bde978d37b4f91a836acaf775fc74f354e90f431169da56f62017  /mnt/primary/integrity.bin`

Therefore, the manifest matches the actual primary file and does not match the deliberately modified secondary file.

## 7. Post-run storage state

### Mounts

- `/dev/loop0` on `/mnt/primary`, XFS
- `/dev/loop1` on `/mnt/secondary`, XFS

### Disk space

- `/mnt/primary`: 960M, 125M used, 836M available, 13% used
- `/mnt/secondary`: 960M, 101M used, 860M available, 11% used

### Block devices

- `loop0`: XFS UUID `4f126c11-8c7d-4974-83aa-200b6c977a75`, mounted at `/mnt/primary`
- `loop1`: XFS UUID `d9023498-ebf4-4403-8d9d-41df97a4d0ab`, mounted at `/mnt/secondary`
- The underlying host disk also showed `/sda1`, `/sda2`, `/sda3`; `/sda2` contained `/boot` and `/sda3` contained root/swap LVM members.

### Storage files

Primary:

- `integrity.bin`: 10M
- `integrity.sha256`: 93 bytes
- `testfile`: 50M

Secondary:

- `integrity.bin`: 5 bytes, intentionally overwritten
- `integrity.sha256`: 93 bytes
- `testfile`: 50M

## 8. Kernel findings

Kernel diagnostics were collected after the test. The 30-line `dmesg` tail contained a pre-test systemd-journald coredump/restart sequence timestamped **14:10:16** local time, including a watchdog result and journal file corruption/unclean shutdown recovery. No kernel log entry in the captured tail was timestamped at the 14:29 test run.

A one-run tail is not sufficient to establish whether the earlier journald event is related to storage or to current operation. No storage I/O error or loop-device failure appeared in the captured kernel tail.

## 9. Failures and limitations

- **Test result:** nonzero exit code 1 due solely to the expected checksum mismatch assertion.
- **No cleanup performed:** intentionally modified secondary file remains as requested.
- **Kernel evidence:** only the last 30 messages are available; no run-scoped kernel journal was collected.
- **Timestamped journal finding:** the recovered journald event predates this test and cannot be proven related to it from the captured evidence.
- **Diagnostic collection:** one initial post-run collection encountered a local Windows Python console encoding limitation; the collection was rerun and completed with exit code 0.

## 10. Recommended next actions

1. Treat this run as fault-injection detection success and not as a storage pass.
2. Investigate the earlier journald coredump independently if journald stability is part of the acceptance criteria.
3. For a clean integrity-test rerun, restore `/mnt/secondary/integrity.bin` from `/mnt/primary/integrity.bin` only if authorized and intentional, then rerun the test suite.
4. If performing another fault-injection test, capture a longer kernel log or a journal timestamp window around the run to establish event correlation.
