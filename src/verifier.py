"""
Verifier - Uploads test files to sandbox and runs verification.
"""

import os
import time

from sandbox_client import SandboxClient


TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")


def run_verifier(sandbox: SandboxClient) -> int:
    """
    Run the verification tests in the sandbox.

    Args:
        sandbox: SandboxClient instance

    Returns:
        1 if all tests pass (reward), 0 if any fail
    """
    print("[verifier] Uploading test files...")

    # Upload test files
    test_files = ["test_outputs.py", "positive_probe.c", "negative_probe.c"]
    for filename in test_files:
        local_path = os.path.join(TESTS_DIR, filename)
        remote_path = f"/tests/{filename}"
        sandbox.upload_file(local_path, remote_path)
        print(f"[verifier]   Uploaded {filename} -> {remote_path}")

    # Install test dependencies
    print("[verifier] Installing test dependencies...")
    result = sandbox.exec_command(
        "apt-get update && apt-get install -y curl binutils",
        timeout=120
    )
    if result["exit_code"] != 0:
        print(f"[verifier] Warning: apt-get failed: {result['stderr'][:200]}")

    # Install uv
    print("[verifier] Installing uv...")
    result = sandbox.exec_command(
        "curl -LsSf https://astral.sh/uv/0.9.5/install.sh | sh",
        timeout=60
    )
    if result["exit_code"] != 0:
        print(f"[verifier] Warning: uv install failed: {result['stderr'][:200]}")

    # Run pytest
    print("[verifier] Running verification tests...")
    result = sandbox.exec_command(
        'export PATH="$HOME/.local/bin:$PATH" && '
        "uvx -p 3.13 -w pytest==8.4.1 pytest /tests/test_outputs.py -rA -v",
        timeout=120
    )

    print(f"[verifier] Test exit code: {result['exit_code']}")
    if result["stdout"]:
        print(f"[verifier] Test output:\n{result['stdout']}")
    if result["stderr"]:
        print(f"[verifier] Test stderr:\n{result['stderr'][:500]}")

    reward = 1 if result["exit_code"] == 0 else 0
    print(f"[verifier] Reward: {reward}")
    return reward
