# 问题排查

## 常见问题

### 1. `LimitExceeded.SandboxInstance` — 实例配额超限

**错误信息：**
```
Sandbox instance quota exceeded. Current: 10, Max: 10
```

**原因：** 运行中的沙箱实例过多，达到账号上限。

**解决：**
```bash
make clean
```
或在 [AGS 控制台](https://console.cloud.tencent.com/ags) 手动停止实例。

---

### 2. `ResourceUnavailable.SandboxTool` — 工具未就绪

**错误信息：**
```
Sandbox sdt-xxx is not active, current status: CREATING
```

**原因：** 工具刚创建，尚未完成初始化。

**解决：** 代码已自动等待工具激活。如持续出现，等待 30-60 秒后重试。

---

### 3. `InvalidParameter` — 探针配置错误

**错误信息：**
```
Probe: ReadyTimeoutMs must be at most 30000
FailureThreshold must be at most 100
```

**原因：** 健康探针参数超出 AGS 限制。

**解决：** 确保 `sandbox_manager.py` 中的探针配置：
- `ReadyTimeoutMs <= 30000`
- `FailureThreshold <= 100`
- `ProbeTimeoutMs <= 5000`
- `ProbePeriodMs >= 100`

---

### 4. Docker push `denied: requested access to the resource is denied`

**原因：** TCR 命名空间不存在或凭据错误。

**解决：**
1. 在 TCR 控制台创建命名空间
2. 重新登录：`docker login lily-tcr.tencentcloudcr.com --username <用户名> --password <令牌>`
3. 确认命名空间名称与镜像路径一致

---

### 5. Docker build 卡在 `load metadata for docker.io/library/ubuntu:24.04`

**原因：** 无法访问 Docker Hub（国内网络问题）。

**解决：**
```bash
# 启动代理
startvpn

# 重启 Docker 以加载代理配置
systemctl restart docker

# 或手动先拉取镜像
docker pull ubuntu:24.04
```

---

### 6. `apt-get` 在沙箱内执行失败（exit code 100）

**原因：** 包管理器锁文件冲突或 locale 问题。

**解决：** Agent 应自动处理：
```bash
dpkg --configure -a
apt-get update
apt-get install -y <packages>
```

如持续出现，可能需要重启沙箱实例。

---

### 7. Agent 超时 — 任务在 40 分钟内未完成

**原因：** CompCert 编译较复杂，Agent 可能卡在循环或执行了低效步骤。

**解决：**
- 增大 `src/agent.py` 中的 `MAX_STEPS`
- 增大 `AGENT_TIMEOUT`（默认 2400s = 40 分钟）
- 增大 `src/sandbox_manager.py` 中的 `INSTANCE_TIMEOUT`
- 检查 Agent 日志定位卡住的位置

---

### 8. 实例 RUNNING 后健康检查失败

**错误信息：**
```
Sandbox health check failed after 60s
```

**原因：** `cmd_server.py` 未在容器内启动，或网络路由问题。

**解决：**
1. 本地验证镜像：`docker run -p 8080:8080 <image>` 然后 `curl localhost:8080/health`
2. 在 AGS 控制台查看实例日志
3. 确认 Dockerfile 暴露了 8080 端口且工具配置了正确端口

---

### 9. LLM API 错误（连接超时、频率限制）

**原因：** TokenHub/kimi-k2.5 API 暂时不可用。

**解决：** Agent 自动重试（5 秒间隔）。如持续出现：
- 检查 TokenHub 服务状态
- 验证 API Key 有效性
- 确认是否触发了频率限制

---

### 10. `ToolId` 或 `InstanceId` 找不到

**原因：** SDK 响应结构字段名不匹配。

**解决：** AGS SDK 使用以下响应字段名：
- 工具列表：`resp.SandboxToolSet`（不是 `ToolSet`）
- 实例列表：`resp.InstanceSet`
- 启动实例：`resp.Instance.InstanceId`
- 令牌：`resp.Token`

---

## 调试技巧

### 手动测试沙箱连通性

```python
from src.sandbox_client import SandboxClient
client = SandboxClient("<instance_id>", "ap-beijing", "<token>")
print(client.health_check())
result = client.exec_command("echo hello")
print(result)
```

### 列出运行中的实例

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

### 本地测试 Docker 镜像

```bash
docker run -d -p 8080:8080 lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest

# 测试健康检查
curl http://localhost:8080/health

# 测试命令执行
curl -X POST http://localhost:8080/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "echo hello world"}'
```
