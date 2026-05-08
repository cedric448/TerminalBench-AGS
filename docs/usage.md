# Usage Guide

## Prerequisites

1. **Python 3.11+** with pip
2. **Docker** installed and running
3. **Tencent Cloud Account** with:
   - AGS service enabled in ap-beijing region
   - SecretId/SecretKey with AGS permissions
   - TCR (Tencent Container Registry) instance for custom images
   - CAM Role allowing AGS to pull from TCR
4. **TokenHub Access** for kimi-k2.5 model

## Initial Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `tencentcloud-sdk-python>=3.1.32` — AGS control plane SDK
- `openai>=1.0.0` — LLM API client (OpenAI-compatible)
- `requests` — HTTP client for sandbox communication

### 2. Configure Environment Variables

```bash
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-beijing"
```

### 3. Build and Push Docker Image

First time only (or when updating the sandbox image):

```bash
# Login to TCR
docker login lily-tcr.tencentcloudcr.com --username <your_username> --password <your_token>

# Build image
make build

# Push to registry
make push
```

The Dockerfile creates a minimal ubuntu:24.04 image with python3, curl, wget, git, and the command execution server.

### 4. TCR Namespace Setup

Ensure the `terminalbench` namespace exists in your TCR registry. Create it via the TCR console if needed.

### 5. CAM Role Setup

AGS needs a role to pull images from your TCR. The role ARN should be configured in `src/sandbox_manager.py`:

```python
ROLE_ARN = "qcs::cam::uin/<your_uin>:roleName/<your_role>"
```

## Running the Benchmark

### Full Run

```bash
make run
```

Or directly:

```bash
cd src && python run_bench.py
```

### What Happens

1. **Tool Creation** — Creates an AGS sandbox tool (skipped if already exists)
2. **Instance Start** — Launches a sandbox container from the tool
3. **Wait for Ready** — Polls until instance is RUNNING and health check passes
4. **Agent Execution** — LLM agent receives the task instruction and starts executing commands
5. **Verification** — Uploads test files and runs pytest to validate the build
6. **Cleanup** — Stops the sandbox instance

### Expected Output

```
============================================================
Terminal Bench Demo - compile-compcert
Using Tencent Cloud AGS + kimi-k2.5
============================================================

[main] Step 1: Creating/finding sandbox tool...
[sandbox_manager] Found existing tool: sdt-xxxxxxxx
[main] Tool ID: sdt-xxxxxxxx

[main] Step 2: Starting sandbox instance...
[sandbox_manager] Instance started: <instance_id>

[main] Step 3: Waiting for instance to be ready...
[sandbox_manager] Instance ... status: RUNNING

[main] Step 4: Acquiring access token...
[main] Step 5: Connecting to sandbox...
[main] Sandbox health check passed

[main] Step 6: Running agent...
[agent] Step 1/50 (elapsed: 0s)
[agent] Executing: uname -a && mkdir -p /tmp/CompCert
...
(agent executes ~15-30 steps over 15-40 minutes)
...
[agent] Agent finished: Task is complete.

[main] Step 7: Running verifier...
[verifier] Uploading test files...
[verifier] Running verification tests...
[verifier] Reward: 1

============================================================
RESULT: PASS
Agent time: 1234s
Reward: 1
============================================================
```

### Cleanup Resources

```bash
make clean
```

This stops all running instances and deletes the sandbox tool.

## Customization

### Changing the LLM Model

Edit `src/agent.py`:

```python
client = OpenAI(
    api_key="your_api_key",
    base_url="your_base_url"
)
# In the create call:
model="your-model-name"
```

### Changing the Task

Edit the `INSTRUCTION` variable in `src/run_bench.py`:

```python
INSTRUCTION = """Your custom task instruction here."""
```

### Adjusting Timeouts

In `src/agent.py`:
- `MAX_STEPS = 50` — Maximum agent iterations
- `AGENT_TIMEOUT = 2400` — Total agent timeout (seconds)
- `COMMAND_TIMEOUT = 300` — Per-command timeout (seconds)

### Changing Sandbox Resources

In `src/sandbox_manager.py`:
```python
resource_config.CPU = "4"       # CPU cores
resource_config.Memory = "8Gi"  # Memory
```
