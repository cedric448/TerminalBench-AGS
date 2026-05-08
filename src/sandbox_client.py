"""
Sandbox Client - HTTP client for executing commands in AGS sandbox.
Communicates with cmd_server.py running inside the container.
"""

import json
import base64
import requests


class SandboxClient:
    """Client for communicating with the command server in an AGS sandbox instance."""

    def __init__(self, instance_id, region, access_token):
        self.base_url = f"https://8080-{instance_id}.{region}.tencentags.com"
        self.headers = {
            "X-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    def health_check(self):
        """Check if the sandbox is responsive."""
        try:
            resp = requests.get(
                f"{self.base_url}/health",
                headers=self.headers,
                timeout=10
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def exec_command(self, command, timeout=300, workdir="/"):
        """
        Execute a bash command in the sandbox.

        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds
            workdir: Working directory for the command

        Returns:
            dict with keys: stdout, stderr, exit_code
        """
        resp = requests.post(
            f"{self.base_url}/exec",
            headers=self.headers,
            json={"command": command, "timeout": timeout, "workdir": workdir},
            timeout=timeout + 30  # HTTP timeout slightly longer than command timeout
        )
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, local_path, remote_path):
        """
        Upload a local file to the sandbox.

        Args:
            local_path: Path to local file
            remote_path: Destination path in sandbox
        """
        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        resp = requests.post(
            f"{self.base_url}/upload",
            headers=self.headers,
            json={"path": remote_path, "content": content},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def upload_content(self, content, remote_path):
        """
        Upload string content directly to the sandbox.

        Args:
            content: String content to upload
            remote_path: Destination path in sandbox
        """
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        resp = requests.post(
            f"{self.base_url}/upload",
            headers=self.headers,
            json={"path": remote_path, "content": encoded},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def download_file(self, remote_path):
        """
        Download a file from the sandbox.

        Args:
            remote_path: Path to file in sandbox

        Returns:
            bytes content of the file
        """
        resp = requests.get(
            f"{self.base_url}/download",
            headers=self.headers,
            params={"path": remote_path},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise FileNotFoundError(data["error"])
        return base64.b64decode(data["content"])
