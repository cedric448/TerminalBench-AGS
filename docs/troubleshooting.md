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
cd src && python3 sandbox_manager.py stop-all
```

---

### 2. `ResourceUnavailable.SandboxTool` — 工具未就绪

**错误信息：**
```
Sandbox sdt-xxx is not active, current status: CREATING
```

**原因：** 工具刚创建，尚未完成初始化（含 StorageVolume 时约需 10-15 秒）。

**解决：** 代码已自动等待工具激活（最长 120 秒）。

---

### 3. Tool 创建 FAILED — `StatusReason: InternalError`

**原因：** 以下场景会导致工具创建失败：
- `sandbox-code:latest` 作为 `custom` 类型工具的基础镜像（仅支持 `code-interpreter` 类型）
- 镜像 digest 无法解析

**解决：** 使用自己的 enterprise 镜像作为 custom 工具基础镜像。

---

### 4. `InternalError` — 实例启动失败

**可能原因：**
- enterprise 镜像作为 StorageVolume 时需要 RoleArn 有 TCR 拉取权限
- 未声明 Ports 但健康探针引用了端口
- `FailedOperation.ContainerStart: port binding failed` — 需要在 CustomConfiguration 中声明端口

**解决：**
```python
# 确保声明端口
port1 = models.PortConfiguration()
port1.Name = "http"
port1.Port = 8080
port1.Protocol = "TCP"
custom_config.Ports = [port1]
```

---

### 5. Docker push `denied: requested access to the resource is denied`

**原因：** TCR 命名空间不存在或凭据错误。

**解决：**
1. 在 TCR 控制台创建命名空间
2. 重新登录：`docker login lily-tcr.tencentcloudcr.com`
3. 确认命名空间名称与镜像路径一致

---

### 6. Docker build 卡在 `load metadata for docker.io/library/ubuntu:24.04`

**原因：** 无法访问 Docker Hub（国内网络问题）。

**解决：**
```bash
# 启动代理
startvpn

# 或手动先拉取镜像
docker pull ubuntu:24.04
```

---

### 7. `apt-get` 在沙箱内执行失败（exit code 100）

**原因：** 包管理器锁文件冲突或 locale 问题。

**解决：** Agent 应自动处理：
```bash
dpkg --configure -a
apt-get update
apt-get install -y <packages>
```

---

### 8. Agent 超时 — 任务在 40 分钟内未完成

**原因：** CompCert 编译较复杂，Agent 可能卡在循环或执行了低效步骤。

**解决：**
- 增大 `src/agent.py` 中的 `MAX_STEPS`
- 增大 `AGENT_TIMEOUT`（默认 2400s = 40 分钟）
- 增大 `src/sandbox_manager.py` 中的 `INSTANCE_TIMEOUT`

---

### 9. 实例 RUNNING 后健康检查失败

**原因：** `cmd_server.py` 未在容器内启动，或网络路由问题。

**解决：**
1. 本地验证镜像：`docker run -p 8080:8080 <image>` 然后 `curl localhost:8080/health`
2. 确认 Dockerfile 暴露了 8080 端口且工具配置了正确端口

---

### 10. StorageVolume 挂载注意事项

**关键限制：**
- `StorageMounts` 配置在 `CreateSandboxToolRequest` 层级，不在 `CustomConfiguration` 内
- enterprise 类型镜像可以作为 volume（需要 RoleArn 有 TCR 权限）
- `sandbox-code:latest` 等 system 镜像不能作为 custom 工具基础镜像

**正确配置示例：**
```python
# StorageMounts 在 req 层级
storage_mount = models.StorageMount()
storage_mount.Name = "task-image"
storage_source = models.StorageSource()
image_source = models.ImageStorageSource()
image_source.Reference = "your-image:tag"
image_source.ImageRegistryType = "enterprise"
storage_source.Image = image_source
storage_mount.StorageSource = storage_source
storage_mount.MountPath = "/task"
req.StorageMounts = [storage_mount]
```

---

## 调试技巧

### 手动测试沙箱连通性

```python
from sandbox_client import SandboxClient
client = SandboxClient("<instance_id>", "ap-beijing", "<token>")
print(client.health_check())
result = client.exec_command("echo hello")
print(result)
```

### 使用 CLI 工具

```bash
# 列出所有工具
cd src && python3 sandbox_manager.py list

# 停止所有实例
cd src && python3 sandbox_manager.py stop-all

# 完整清理
cd src && python3 sandbox_manager.py cleanup
```

### 本地测试 Docker 镜像

```bash
docker run -d -p 8080:8080 lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6

# 测试健康检查
curl http://localhost:8080/health

# 测试命令执行
curl -X POST http://localhost:8080/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "echo hello world"}'
```
