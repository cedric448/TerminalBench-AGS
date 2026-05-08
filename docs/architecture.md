# Architecture

## System Overview

TerminalBench-AGS is an end-to-end benchmark runner that evaluates LLM agents on terminal-based tasks using Tencent Cloud AGS (Agent Sandbox Service) as the execution environment.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Host Machine                                   │
│                                                                       │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐ │
│  │ run_bench.py│───▶│sandbox_mgr.py│───▶│ AGS Control Plane API   │ │
│  │ Orchestrator│    │              │    │ (ags.tencentcloudapi.com)│ │
│  └──────┬──────┘    └──────────────┘    └─────────────────────────┘ │
│         │                                                             │
│         ▼                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐ │
│  │  agent.py   │───▶│sandbox_cli.py│───▶│ AGS Data Plane (HTTP)   │ │
│  │ LLM Agent   │    │ HTTP Client  │    │ 8080-{id}.{r}.tencentags│ │
│  └──────┬──────┘    └──────────────┘    └────────────┬────────────┘ │
│         │                                             │               │
│         ▼                                             ▼               │
│  ┌─────────────┐                        ┌─────────────────────────┐ │
│  │ verifier.py │                        │   AGS Sandbox Instance  │ │
│  │ Test Runner │                        │  ┌───────────────────┐  │ │
│  └─────────────┘                        │  │  cmd_server.py    │  │ │
│                                          │  │  (port 8080)      │  │ │
│                                          │  │  GET /health      │  │ │
│                                          │  │  POST /exec       │  │ │
│                                          │  │  POST /upload     │  │ │
│                                          │  │  GET /download    │  │ │
│                                          │  └───────────────────┘  │ │
│                                          └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Orchestrator (`run_bench.py`)

The main entry point that coordinates the full benchmark lifecycle:
1. Create/find AGS sandbox tool
2. Start sandbox instance and wait for ready
3. Acquire access token
4. Run the LLM agent
5. Run verification tests
6. Report results and cleanup

### 2. Sandbox Manager (`sandbox_manager.py`)

Handles AGS control plane operations via `tencentcloud-sdk-python`:

- **CreateSandboxTool** — Registers a custom sandbox tool with Docker image, health probe, and resource config
- **StartSandboxInstance** — Launches a sandbox instance from the tool
- **DescribeSandboxInstanceList** — Polls instance status until RUNNING
- **AcquireSandboxInstanceToken** — Gets HTTP access token
- **StopSandboxInstance** — Stops and cleans up instances
- **DeleteSandboxTool** — Removes the tool definition

### 3. Sandbox Client (`sandbox_client.py`)

HTTP client that communicates with `cmd_server.py` inside the sandbox:

- `exec_command(cmd)` — Execute bash commands, returns stdout/stderr/exit_code
- `upload_file(local, remote)` — Upload files to sandbox (base64 encoded)
- `download_file(remote)` — Download files from sandbox
- `health_check()` — Verify sandbox is responsive

### 4. Command Server (`cmd_server.py`)

Runs inside the Docker container. A minimal HTTP server (Python stdlib only) providing:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Readiness probe for AGS |
| `/exec` | POST | Execute shell commands |
| `/upload` | POST | Upload files (base64) |
| `/download` | GET | Download files |

### 5. LLM Agent (`agent.py`)

An agentic loop using kimi-k2.5 (via TokenHub OpenAI-compatible API):

- System prompt instructs the agent to complete terminal tasks
- Single tool: `execute_command(command: str)`
- Loop: LLM generates tool_call → execute in sandbox → return result → repeat
- Terminates when LLM responds without tool_call or max steps reached
- Timeout: 2400s (40 min), Max steps: 50

### 6. Verifier (`verifier.py`)

After the agent finishes, runs verification:
1. Uploads test files to sandbox
2. Installs pytest via uv
3. Runs test suite checking CompCert installation
4. Returns reward: 1 (pass) or 0 (fail)

## Data Flow

```
1. Orchestrator creates AGS tool (one-time)
2. Orchestrator starts instance → AGS pulls Docker image → container starts
3. AGS health probe hits cmd_server /health → instance marked RUNNING
4. Agent calls kimi-k2.5 API → gets tool_call → sandbox_client POSTs to /exec
5. cmd_server runs bash command → returns JSON response
6. Agent loop continues until task complete
7. Verifier uploads tests → runs pytest → collects reward
8. Orchestrator stops instance
```

## AGS Configuration

| Parameter | Value |
|-----------|-------|
| Tool Name | `terminal-bench-compcert` |
| Image | `lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest` |
| Registry Type | enterprise |
| Resources | 2 CPU, 4Gi memory |
| Network | PUBLIC (internet access for downloads) |
| Probe | HTTP GET /health:8080 |
| Timeout | 40 minutes |
| RoleArn | `qcs::cam::uin/100008634787:roleName/ags-tcr-full` |

## Security Notes

- The sandbox runs with internet access (needed to download CompCert sources)
- Command execution has a per-command timeout (300s default)
- The container runs as root (required for apt-get)
- Access to the sandbox requires a time-limited token from AGS
