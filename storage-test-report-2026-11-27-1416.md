# Storage I/O Test Report

**Run date:** 2026-11-27  
**Run time:** approximately 14:16 (workspace/VM local time)  
**Target:** Rocky Linux VM accessed by `ssh_client.py`  
**Overall result:** Write, integrity-file generation, and replication succeeded. The test process exited with code `1` because its deliberate corruption injection was correctly detected by the final checksum assertion.

## Execution summary

| Check | Result | Evidence |
|---|---|---|
| Python compile check | Passed | `python -m py_compile` completed for `ssh_client.py`, `test_storage_io.py`, and `storage_tools.py`. |
| SSH connectivity | Passed | `ssh_client.py` completed its remote `ls -l` command; exit code `0`, empty stderr. |
| Storage preflight | Passed | Both storage paths were mounted read-write and had approximately 850 MiB free before execution. |
| Storage I/O test | Expected assertion failure | Exit code `1`; all write/replication steps passed, then the explicit primary/secondary hash comparison detected the injected mismatch. |
| Post-run diagnostics | Collected | Mount, capacity, block-device, file listing, checksum, and kernel-log output captured. |

## Preflight

Mount check reported:

```text
/dev/loop0 on /mnt/primary type xfs (rw,...)
/dev/loop1 on /mnt/secondary type xfs (rw,...)
```

Both mounts were XFS and read-write.

Pre-run capacity:

```text
Filesystem     Type  Size  Used Avail Use% Mounted on
/dev/loop0     xfs   960M  111M  850M  12% /mnt/primary
/dev/loop1     xfs   960M  101M  860M  11% /mnt/secondary
```

## Test results

The test ran these operations in order:

1. **Primary write — passed.** Wrote a 50 MiB zero-filled file to `/mnt/primary/testfile`.
2. **Integrity data generation — passed.** Wrote 10 MiB of random data to `/mnt/primary/integrity.bin` and created `/mnt/primary/integrity.sha256`.
3. **Replication — passed.** `rsync -axHAX /mnt/primary/ /mnt/secondary/` returned success.
4. **Fault injection — passed.** The script deliberately replaced `/mnt/secondary/integrity.bin` with the text `dddd`.
5. **Integrity comparison — expected failure.** Direct SHA-256 values differed; `check_sha256_match()` raised `AssertionError`, producing process exit code `1`.

Direct comparison output:

```text
9572ebe91aba469ca5d907e52833265c62f7e6713d3c296e890558def771b6a0  /mnt/primary/integrity.bin
5a4374779c218ee174d4dd904f61579f3f54cc4e62f5fe0bfe50f665e066095c  /mnt/secondary/integrity.bin
```

The test reported:

```text
HASH MISMATCH - TEST FAILED:
primary=9572ebe91aba469ca5d907e52833265c62f7e6713d3c296e890558def771b6a0,
secondary=5a4374779c218ee174d4dd904f61579f3f54cc4e62f5fe0bfe50f665e066095c
```

Thus, the nonzero exit is consistent with the test's intentional fault-injection scenario. It does not indicate that the preceding write or replication commands failed.

## Post-run storage state

Capacity after the test:

```text
/mnt/primary:   960M total, 125M used, 836M available (13%)
/mnt/secondary: 960M total, 101M used, 860M available (11%)
```

Block-device diagnostics identified `/dev/loop0` as the XFS filesystem mounted at `/mnt/primary` and `/dev/loop1` as the XFS filesystem mounted at `/mnt/secondary`.

Files observed:

```text
/mnt/primary:
  integrity.bin       10M
  integrity.sha256    93 bytes
  testfile            50M

/mnt/secondary:
  integrity.bin       5 bytes
  integrity.sha256    93 bytes
  testfile            50M
```

The secondary integrity file remains deliberately corrupted after the run. No cleanup or repair was performed.

## Manifest verification caveat

Direct hashing of both files above proves that their contents differ. However, the script-generated `integrity.sha256` manifest contains the absolute primary path (`/mnt/primary/integrity.bin`). Checks of that manifest from either mount therefore verified the primary file and returned:

```text
/mnt/primary/integrity.bin: OK
```

That manifest check does **not** validate the secondary copy. The direct two-file hash comparison is the valid evidence for the mismatch.

## Kernel diagnostics

The latest captured kernel-log entries include repeated `systemd-journald` watchdog failures and aborts, with a restart counter reaching **15**, followed by journal replacement after a message that the journal was corrupted or shut down uncleanly. The logged event time is **2026-11-27 14:10:16**, before this test's approximately 14:16 run. These messages cannot be attributed to this test based on the available timestamps and should be investigated separately.

## Conclusion and recommended follow-up

- Storage preflight, SSH connectivity, primary write, integrity-file creation, and replication all succeeded.
- The test correctly detected the intentionally introduced corruption; its final exit code was `1` as a result.
- Investigate the recurring `systemd-journald` watchdog abort/restart activity separately.
- If manifest verification is intended to check the secondary copy, generate or adjust the manifest so its path is relative or points to the secondary file. The current manifest points to the primary file.
