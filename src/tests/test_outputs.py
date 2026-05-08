"""
Terminal Bench CompCert verification tests.
Tests that CompCert was built correctly and is functional.
"""

import os
import subprocess
import tempfile
import pytest

CCOMP_PATH = "/tmp/CompCert/ccomp"
TESTS_DIR = "/tests"


def run_cmd(cmd, timeout=60, check=False):
    """Run a shell command and return the result."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result


class TestCompCertInstallation:
    """Test that CompCert is correctly installed and functional."""

    def test_compcert_exists_and_executable(self):
        """CompCert binary must exist at /tmp/CompCert/ccomp and be executable."""
        assert os.path.exists(CCOMP_PATH), f"CompCert not found at {CCOMP_PATH}"
        assert os.access(CCOMP_PATH, os.X_OK), f"{CCOMP_PATH} is not executable"

        # Verify it's a real binary (not a script or symlink to something else)
        result = run_cmd(f"file {CCOMP_PATH}")
        assert result.returncode == 0
        # Should be an ELF binary
        assert "ELF" in result.stdout, f"ccomp is not an ELF binary: {result.stdout}"

    def test_compcert_valid_and_functional(self):
        """CompCert must compile the positive probe and produce correct output."""
        probe_src = os.path.join(TESTS_DIR, "positive_probe.c")
        assert os.path.exists(probe_src), f"Test file not found: {probe_src}"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_bin = os.path.join(tmpdir, "positive_probe")

            # Compile with CompCert
            result = run_cmd(
                f"{CCOMP_PATH} -o {output_bin} {probe_src}",
                timeout=60
            )
            assert result.returncode == 0, (
                f"CompCert failed to compile positive_probe.c:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            assert os.path.exists(output_bin), "Compiled binary not produced"

            # Run the compiled binary
            test_input = "abcdef"
            expected_reversed = "fedcba"
            result = run_cmd(f"{output_bin} {test_input}", timeout=10)
            assert result.returncode == 0, (
                f"Compiled binary exited with code {result.returncode}"
            )
            assert f"Hello CompCert:{expected_reversed}" in result.stdout, (
                f"Unexpected output: {result.stdout}"
            )

    def test_compcert_rejects_unsupported_feature(self):
        """CompCert must reject code with variable-length arrays (VLAs)."""
        probe_src = os.path.join(TESTS_DIR, "negative_probe.c")
        assert os.path.exists(probe_src), f"Test file not found: {probe_src}"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_bin = os.path.join(tmpdir, "negative_probe")

            # CompCert should fail to compile VLA code
            result = run_cmd(
                f"{CCOMP_PATH} -o {output_bin} {probe_src}",
                timeout=60
            )
            assert result.returncode != 0, (
                "CompCert should reject variable-length arrays but compiled successfully"
            )
