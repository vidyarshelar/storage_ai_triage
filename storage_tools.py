from ssh_client import run_command


def _run_storage_check(command: str, label: str) -> str:
    exit_code, output, error = run_command(command)
    if exit_code == 0:
        return f"{label}:\n{output.strip()}"
    return f"Failed to {label.lower()}: {error.strip() or f'exit code {exit_code}'}"


def get_kernel_logs() -> str:
    """Return the last 30 kernel log messages from the Rocky Linux VM."""
    return _run_storage_check("dmesg -T | tail -n 30", "Kernel logs")


def check_disk_space() -> str:
    """Return filesystem type and disk usage for the primary and secondary mounts."""
    return _run_storage_check(
        "df -hT /mnt/primary /mnt/secondary", "Disk space usage"
    )


def check_mount_points() -> str:
    """Return mount entries for the primary and secondary storage paths."""
    return _run_storage_check(
        "mount | grep -E '/mnt/primary|/mnt/secondary'", "Mount points"
    )


def check_block_devices() -> str:
    """Return filesystem and mount information for all block devices."""
    return _run_storage_check("lsblk -f", "Block devices")


def inspect_storage_files() -> str:
    """List file sizes, permissions, and timestamps inside both storage paths."""
    return _run_storage_check(
        "ls -lh /mnt/primary /mnt/secondary", "Storage files"
    )
