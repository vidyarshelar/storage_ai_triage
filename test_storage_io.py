from ssh_client import run_command

def test_primary_storage_write():
    cmd="dd if=/dev/zero of=/mnt/primary/testfile bs=1M count=50 conv=fdatasync"
    exit_code, output, error = run_command(cmd)
    if exit_code == 0:
        print("Write test to primary storage successful.")
    else:
        raise RuntimeError(f"Write test failed: {error.strip()}")

def test_data_integrity():
    cmd="head -c 10M /dev/urandom > /mnt/primary/integrity.bin && sha256sum /mnt/primary/integrity.bin > /mnt/primary/integrity.sha256"
    exit_code, output, error = run_command(cmd)
    if exit_code == 0:
        print(f"Data integrity test successful: {output.strip()}")
    else:
        raise RuntimeError(f"Data integrity check failed: {error.strip()}")

def test_secondary_replication_sync():
    cmd="rsync -axHAX /mnt/primary/ /mnt/secondary/"
    exit_code, output, error = run_command(cmd) 
    if exit_code == 0:
        print(f"Resync successful: {output.strip()}")
    else:
        raise RuntimeError(f"Resync failed: {error.strip()}")
    #Adding explicitly to check test fail scenario by injecting error
    cmd2="echo dddd > /mnt/secondary/integrity.bin"
    exit_code, output, error = run_command(cmd2)
    if exit_code == 0:
        print(f"Secondary storage modified successfully: {output.strip()}")
        #test_secondary_replication_sync()
    else:
        raise RuntimeError(f"Modification of secondary storage failed: {error.strip()}")
        

def check_sha256_match():
    print("Checking SHA-256 checksums for primary and secondary storage...")
    command = (
        "sha256sum /mnt/primary/integrity.bin "
        "/mnt/secondary/integrity.bin"
    )
    exit_code, output, error = run_command(command)
    print(f"Command output and exit code: {output.strip()}, {exit_code}")
    if exit_code != 0:
        details = error.strip() or output.strip() or f"exit code {exit_code}"
        raise RuntimeError(f"Checksum command failed: {details}")

    hashes = []
    for line in output.splitlines():
        parts = line.split(maxsplit=1)
        if parts:
            hashes.append(parts[0])

    if len(hashes) != 2:
        raise RuntimeError(f"Expected two checksum results; received: {output!r}")

    primary_hash, secondary_hash = hashes
    if primary_hash != secondary_hash:
        message = (
        "HASH MISMATCH - TEST FAILED: "
        f"primary={primary_hash}, secondary={secondary_hash}"
        )
        print(message, flush=True)
        raise AssertionError(message)
   # return f"SHA-256 checksums match: {primary_hash}"

if __name__ == "__main__":
    test_primary_storage_write()
    test_data_integrity()
    test_secondary_replication_sync()
    check_sha256_match()