# TerminalBench-AGS

Terminal Bench demo running on Tencent Cloud AGS (Agent Sandbox Service). An LLM agent (kimi-k2.5) autonomously completes terminal-based tasks inside a cloud sandbox, with automated verification.

## Overview

This project demonstrates how to run [Terminal Bench](https://github.com/harbor-framework/terminal-bench-2) evaluations using Tencent Cloud AGS as the sandbox infrastructure. The demo task is **compile-compcert** — building the CompCert verified C compiler from source.

### Architecture

```
┌──────────────────────┐     ┌──────────────────────────────┐     ┌──────────────────────┐
│   LLM Agent          │────▶│  AGS Sandbox                 │────▶│  Verifier            │
│   (kimi-k2.5)        │◀────│  (custom Docker image)       │     │  (pytest in sandbox) │
└──────────────────────┘     └──────────────────────────────┘     └──────────────────────┘
```

- **Agent**: Uses kimi-k2.5 via Tencent TokenHub (OpenAI-compatible API) with function calling
- **Sandbox**: AGS custom sandbox tool running ubuntu:24.04 + HTTP command server
- **Verifier**: Uploads pytest tests and validates CompCert was built correctly

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for building sandbox image)
- Tencent Cloud account with AGS enabled
- Access to Tencent TokenHub (kimi-k2.5)

### Setup

```bash
# Install dependencies
make setup

# Set environment variables
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-beijing"

# Build and push Docker image (first time only)
make build-push
```

### Run

```bash
make run
```

This will:
1. Create an AGS sandbox tool (or reuse existing)
2. Start a sandbox instance
3. Run the LLM agent to build CompCert
4. Verify the build with pytest
5. Report PASS/FAIL and cleanup

### Cleanup

```bash
make clean
```

## Project Structure

```
.
├── README.md
├── Dockerfile              # Sandbox container image
├── Makefile                # Build, push, run commands
├── requirements.txt        # Python dependencies
├── src/
│   ├── run_bench.py        # Main orchestrator
│   ├── agent.py            # LLM agent (kimi-k2.5 + function calling)
│   ├── sandbox_manager.py  # AGS control plane (create tool, start/stop instance)
│   ├── sandbox_client.py   # HTTP client for sandbox command execution
│   ├── cmd_server.py       # In-container HTTP command server
│   ├── verifier.py         # Test verification runner
│   └── tests/
│       ├── test_outputs.py     # Pytest verification suite
│       ├── positive_probe.c    # CompCert compilation test
│       └── negative_probe.c    # VLA rejection test
└── docs/
    ├── architecture.md     # System architecture
    ├── usage.md            # Detailed usage guide
    └── troubleshooting.md  # Common issues and fixes
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `TENCENTCLOUD_SECRET_ID` | Tencent Cloud SecretId | (required) |
| `TENCENTCLOUD_SECRET_KEY` | Tencent Cloud SecretKey | (required) |
| `TENCENTCLOUD_REGION` | AGS region | `ap-beijing` |

## Documentation

- [Architecture](docs/architecture.md) - System design and component overview
- [Usage Guide](docs/usage.md) - Detailed setup and operation guide
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## License

MIT
