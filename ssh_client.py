import paramiko
import os
import threading


# Set your SSH connection details here.
HOST = "127.0.0.1"
PORT = 2222
USERNAME = "root"
PASSWORD = "root123"
_SSH_LOCK = threading.Lock()

def run_command(cmd, timeout=30):
    """Run a command over SSH and return (exit_code, stdout, stderr)."""
    with _SSH_LOCK:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
            hostname=HOST,
            port=PORT,
            username=USERNAME,
            password=PASSWORD,
            timeout=10,
            banner_timeout=10,
        )
            _, stdout, stderr = client.exec_command(cmd, timeout=15)
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()
            return exit_code, output, error
        finally:
            client.close()


def get_os_name():
    exit_code, output, error = run_command("uname -a")
    if exit_code == 0:
        return output.strip()
    print(f"Command failed with exit code {exit_code}: {error.strip()}")


if __name__ == "__main__":
    code, output, error = run_command("ls -l")
    print(f"Exit code: {code}")
    print(f"stdout: {output}")
    print(f"stderr: {error}")
