# Troubleshooting

## Common Issues

### 1. `LimitExceeded.SandboxInstance` — Instance quota exceeded

**Error:**
```
Sandbox instance quota exceeded. Current: 10, Max: 10
```

**Cause:** Too many sandbox instances are running. AGS has a per-account limit.

**Fix:**
```bash
make clean
```
Or manually stop instances in the [AGS Console](https://console.cloud.tencent.com/ags).

---

### 2. `ResourceUnavailable.SandboxTool` — Tool not active

**Error:**
```
Sandbox sdt-xxx is not active, current status: CREATING
```

**Cause:** The tool was just created and hasn't finished initialization.

**Fix:** The code now automatically waits for tool activation. If this persists, wait 30-60 seconds and retry.

---

### 3. `InvalidParameter` — Probe configuration errors

**Error:**
```
Probe: ReadyTimeoutMs must be at most 30000
FailureThreshold must be at most 100
```

**Cause:** Health probe values exceed AGS limits.

**Fix:** Ensure probe config in `sandbox_manager.py` uses:
- `ReadyTimeoutMs <= 30000`
- `FailureThreshold <= 100`
- `ProbeTimeoutMs <= 5000`
- `ProbePeriodMs >= 100`

---

### 4. Docker push `denied: requested access to the resource is denied`

**Cause:** TCR namespace doesn't exist or credentials are wrong.

**Fix:**
1. Create the namespace in TCR console
2. Re-login: `docker login lily-tcr.tencentcloudcr.com --username <user> --password <token>`
3. Verify namespace name matches the image path

---

### 5. Docker build timeout on `load metadata for docker.io/library/ubuntu:24.04`

**Cause:** Cannot reach Docker Hub (network issue in China).

**Fix:**
```bash
# Start VPN/proxy if available
startvpn

# Restart Docker to pick up proxy settings
systemctl restart docker

# Or pull manually first
docker pull ubuntu:24.04
```

---

### 6. `apt-get` fails inside sandbox with exit code 100

**Cause:** Package manager lock file conflict or locale issues.

**Fix:** The agent should handle this by running:
```bash
dpkg --configure -a
apt-get update
apt-get install -y <packages>
```

If persistent, the sandbox container may need a restart.

---

### 7. Agent timeout — task not completing in 40 minutes

**Cause:** CompCert compilation is complex; the agent might be stuck in a loop or taking inefficient steps.

**Fix:**
- Increase `MAX_STEPS` in `src/agent.py`
- Increase `AGENT_TIMEOUT` (default 2400s = 40min)
- Increase sandbox instance timeout in `src/sandbox_manager.py` (`INSTANCE_TIMEOUT`)
- Check agent logs to identify where it gets stuck

---

### 8. Health check fails after instance is RUNNING

**Error:**
```
Sandbox health check failed after 60s
```

**Cause:** `cmd_server.py` isn't starting inside the container, or network routing issue.

**Fix:**
1. Verify the Docker image builds correctly: `docker run -p 8080:8080 <image>` and test `curl localhost:8080/health`
2. Check AGS instance logs in the console
3. Ensure port 8080 is exposed in Dockerfile and configured in tool ports

---

### 9. LLM API errors (connection timeout, rate limit)

**Cause:** TokenHub/kimi-k2.5 API is temporarily unavailable.

**Fix:** The agent automatically retries with a 5s delay. If persistent:
- Check TokenHub service status
- Verify API key is valid
- Check if you've hit rate limits

---

### 10. `ToolId` or `InstanceId` not found errors

**Cause:** SDK response structure mismatch.

**Fix:** The AGS SDK uses these response field names:
- Tool list: `resp.SandboxToolSet` (not `ToolSet`)
- Instance list: `resp.InstanceSet`
- Start instance: `resp.Instance.InstanceId`
- Token: `resp.Token`

---

## Debugging Tips

### Check sandbox connectivity manually

```python
from src.sandbox_client import SandboxClient
client = SandboxClient("<instance_id>", "ap-beijing", "<token>")
print(client.health_check())
result = client.exec_command("echo hello")
print(result)
```

### List running instances

```python
from src.sandbox_manager import get_client
from tencentcloud.ags.v20250920 import models

client = get_client()
req = models.DescribeSandboxInstanceListRequest()
req.Limit = 100
resp = client.DescribeSandboxInstanceList(req)
for inst in resp.InstanceSet:
    print(f"{inst.InstanceId[:16]} | {inst.ToolName} | {inst.Status}")
```

### Test Docker image locally

```bash
docker run -d -p 8080:8080 lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest

# Test health
curl http://localhost:8080/health

# Test command execution
curl -X POST http://localhost:8080/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "echo hello world"}'
```
