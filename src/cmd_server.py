#!/usr/bin/env python3
"""
Minimal HTTP command execution server for AGS sandbox.
Runs inside the container, provides endpoints for:
- GET /health - readiness probe
- POST /exec - execute shell commands
- POST /upload - upload files
- GET /download - download files
"""

import json
import os
import subprocess
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class CommandHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging to keep output clean
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return b""
        return self.rfile.read(content_length)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_json({"status": "ok"})

        elif parsed.path == "/download":
            params = parse_qs(parsed.query)
            path = params.get("path", [None])[0]
            if not path:
                self._send_json({"error": "path parameter required"}, 400)
                return
            if not os.path.exists(path):
                self._send_json({"error": f"file not found: {path}"}, 404)
                return
            try:
                with open(path, "rb") as f:
                    content = f.read()
                self._send_json({
                    "path": path,
                    "content": base64.b64encode(content).decode("utf-8"),
                    "size": len(content)
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/exec":
            body = self._read_body()
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid JSON"}, 400)
                return

            command = data.get("command")
            if not command:
                self._send_json({"error": "command field required"}, 400)
                return

            timeout = data.get("timeout", 300)
            workdir = data.get("workdir", "/")

            try:
                result = subprocess.run(
                    ["bash", "-c", command],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=workdir,
                    env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
                )
                self._send_json({
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode
                })
            except subprocess.TimeoutExpired:
                self._send_json({
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout}s",
                    "exit_code": -1
                })
            except Exception as e:
                self._send_json({
                    "stdout": "",
                    "stderr": str(e),
                    "exit_code": -1
                })

        elif parsed.path == "/upload":
            body = self._read_body()
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid JSON"}, 400)
                return

            path = data.get("path")
            content = data.get("content")
            if not path or content is None:
                self._send_json({"error": "path and content fields required"}, 400)
                return

            try:
                # Decode base64 content
                file_content = base64.b64decode(content)
                os.makedirs(os.path.dirname(path) or "/", exist_ok=True)
                with open(path, "wb") as f:
                    f.write(file_content)
                os.chmod(path, 0o755)
                self._send_json({"status": "ok", "path": path, "size": len(file_content)})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": "not found"}, 404)


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), CommandHandler)
    print(f"Command server listening on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
