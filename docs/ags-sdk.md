# AGS SDK 完整参考

本文档介绍腾讯云 AGS 的两种 SDK 使用方式：
1. **云 API SDK**（`tencentcloud-sdk-python`）— 控制面操作：创建工具、管理实例
2. **e2b SDK**（`e2b_code_interpreter`）— 数据面操作：在沙箱中执行代码

## 一、云 API SDK（控制面）

### 安装

```bash
pip install 'tencentcloud-sdk-python>=3.1.32'
```

### 初始化客户端

```python
import os
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ags.v20250920 import ags_client, models

# 创建认证对象
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# 配置 HTTP
http_profile = HttpProfile()
http_profile.endpoint = "ags.tencentcloudapi.com"

# 配置客户端
client_profile = ClientProfile()
client_profile.httpProfile = http_profile

# 创建 AGS 客户端
client = ags_client.AgsClient(cred, "ap-beijing", client_profile)
```

### 创建自定义沙箱工具

```python
import json

def create_custom_sandbox_tool(client):
    """创建自定义沙箱工具"""
    req = models.CreateSandboxToolRequest()

    # 基本参数
    req.ToolName = "my-custom-tool"
    req.ToolType = "custom"
    req.Description = "自定义沙箱工具"
    req.DefaultTimeout = "30m"
    req.RoleArn = "qcs::cam::uin/<your_uin>:roleName/<your_role>"

    # 自定义镜像配置
    custom_config = models.CustomConfiguration()
    custom_config.Image = "your-registry.tencentcloudcr.com/namespace/image:tag"
    custom_config.ImageRegistryType = "enterprise"  # enterprise | personal | system
    custom_config.Command = ["python3"]             # 覆盖 ENTRYPOINT
    custom_config.Args = ["/app/server.py"]         # 覆盖 CMD

    # 端口配置
    port = models.PortConfiguration()
    port.Name = "http"
    port.Port = 8080
    port.Protocol = "TCP"
    custom_config.Ports = [port]

    # 环境变量
    env1 = models.EnvVar()
    env1.Name = "DEBIAN_FRONTEND"
    env1.Value = "noninteractive"
    env2 = models.EnvVar()
    env2.Name = "LANG"
    env2.Value = "en_US.UTF-8"
    custom_config.Env = [env1, env2]

    # 资源配置
    resource_config = models.ResourceConfiguration()
    resource_config.CPU = "2"       # CPU 核数
    resource_config.Memory = "4Gi"  # 内存
    custom_config.Resources = resource_config

    # 健康探针配置（必须）
    probe_config = models.ProbeConfiguration()
    http_get = models.HttpGetAction()
    http_get.Path = "/health"
    http_get.Port = 8080
    http_get.Scheme = "HTTP"
    probe_config.HttpGet = http_get
    probe_config.ReadyTimeoutMs = 30000     # 就绪超时（最大 30000）
    probe_config.ProbeTimeoutMs = 2000      # 探针超时
    probe_config.ProbePeriodMs = 500        # 探针间隔
    probe_config.SuccessThreshold = 1       # 成功阈值
    probe_config.FailureThreshold = 100     # 失败阈值（最大 100）
    custom_config.Probe = probe_config

    req.CustomConfiguration = custom_config

    # 网络配置
    network_config = models.NetworkConfiguration()
    network_config.NetworkMode = "PUBLIC"  # PUBLIC | VPC | SANDBOX
    req.NetworkConfiguration = network_config

    # 发送请求
    resp = client.CreateSandboxTool(req)
    print(f"工具创建成功: {resp.ToolId}")
    return resp.ToolId
```

### 查询沙箱工具列表

```python
def list_sandbox_tools(client):
    """查询所有沙箱工具"""
    req = models.DescribeSandboxToolListRequest()
    req.Limit = 100
    req.Offset = 0

    resp = client.DescribeSandboxToolList(req)
    print(f"共 {resp.TotalCount} 个工具")
    for tool in resp.SandboxToolSet:
        print(f"  {tool.ToolId} | {tool.ToolName} | {tool.Status} | {tool.ToolType}")
    return resp.SandboxToolSet
```

### 删除沙箱工具

```python
def delete_sandbox_tool(client, tool_id):
    """删除沙箱工具"""
    req = models.DeleteSandboxToolRequest()
    req.ToolId = tool_id
    resp = client.DeleteSandboxTool(req)
    print(f"工具已删除: {tool_id}")
```

### 启动沙箱实例

```python
def start_sandbox_instance(client, tool_id, timeout="30m"):
    """启动沙箱实例"""
    req = models.StartSandboxInstanceRequest()
    req.ToolId = tool_id
    req.Timeout = timeout  # 实例超时时间

    # 可选：实例级别覆盖配置
    # custom_config = models.CustomConfiguration()
    # custom_config.Image = "override-image:tag"
    # req.CustomConfiguration = custom_config

    resp = client.StartSandboxInstance(req)
    instance_id = resp.Instance.InstanceId
    print(f"实例已启动: {instance_id}")
    return instance_id
```

### 查询沙箱实例列表

```python
def list_sandbox_instances(client, tool_id=None):
    """查询沙箱实例"""
    req = models.DescribeSandboxInstanceListRequest()
    req.Limit = 100
    req.Offset = 0

    resp = client.DescribeSandboxInstanceList(req)
    print(f"共 {resp.TotalCount} 个实例")
    for inst in resp.InstanceSet:
        print(f"  {inst.InstanceId[:20]}... | {inst.ToolName} | {inst.Status}")
    return resp.InstanceSet
```

### 获取实例访问令牌

```python
def acquire_instance_token(client, instance_id):
    """获取沙箱实例的 HTTP 访问令牌"""
    req = models.AcquireSandboxInstanceTokenRequest()
    req.InstanceId = instance_id

    resp = client.AcquireSandboxInstanceToken(req)
    print(f"令牌获取成功，过期时间: {resp.ExpiresAt}")
    return resp.Token
```

### 停止沙箱实例

```python
def stop_sandbox_instance(client, instance_id):
    """停止沙箱实例"""
    req = models.StopSandboxInstanceRequest()
    req.InstanceId = instance_id
    client.StopSandboxInstance(req)
    print(f"实例已停止: {instance_id}")
```

### 访问沙箱实例（HTTP）

```python
import urllib.request

def access_sandbox(instance_id, region, token, port=8080):
    """通过 HTTP 访问沙箱实例"""
    url = f"https://{port}-{instance_id}.{region}.tencentags.com"
    headers = {"X-Access-Token": token}

    req = urllib.request.Request(url=url, headers=headers)
    with urllib.request.urlopen(req) as response:
        print(f"状态码: {response.getcode()}")
        print(f"响应: {response.read().decode('utf-8')}")
```

### 完整生命周期示例

```python
import time

def run_full_lifecycle():
    """完整的沙箱工具 + 实例生命周期"""
    client = create_ags_client()

    # 1. 创建工具
    tool_id = create_custom_sandbox_tool(client)

    # 2. 等待工具就绪
    while True:
        tools = list_sandbox_tools(client)
        tool = next(t for t in tools if t.ToolId == tool_id)
        if tool.Status == "ACTIVE":
            break
        time.sleep(3)

    # 3. 启动实例
    instance_id = start_sandbox_instance(client, tool_id, timeout="1h")

    # 4. 等待实例 RUNNING
    while True:
        instances = list_sandbox_instances(client)
        inst = next(i for i in instances if i.InstanceId == instance_id)
        if inst.Status == "RUNNING":
            break
        time.sleep(5)

    # 5. 获取令牌
    token = acquire_instance_token(client, instance_id)

    # 6. 访问沙箱
    access_sandbox(instance_id, "ap-beijing", token)

    # 7. 清理
    stop_sandbox_instance(client, instance_id)
    delete_sandbox_tool(client, tool_id)
```

---

## 二、e2b SDK（数据面）

e2b SDK 适用于代码解释器类型的沙箱（`code-interpreter`），提供更高级的抽象。

### 安装

```bash
pip install e2b_code_interpreter
```

### 环境配置

```bash
export E2B_API_KEY="your_ags_api_key"
export E2B_DOMAIN="ap-beijing.tencentags.com"
```

### 创建沙箱

```python
from e2b_code_interpreter import Sandbox

# 使用预置模板创建沙箱
sandbox = Sandbox.create(template="code-interpreter-v1", timeout=3600)
print(f"沙箱 ID: {sandbox.sandbox_id}")
```

### 执行代码

```python
# Python
result = sandbox.run_code("""
import numpy as np
data = np.random.randn(100)
print(f"均值: {data.mean():.4f}")
print(f"标准差: {data.std():.4f}")
""")
print(result.logs.stdout)

# JavaScript
result = sandbox.run_code('console.log("Hello from JS")', "js")

# Bash
result = sandbox.run_code("echo hello && uname -a", "bash")
```

### 流式输出

```python
result = sandbox.run_code(
    "for i in range(5): print(f'Step {i}')",
    on_stdout=lambda data: print(f"[stdout] {data}"),
    on_stderr=lambda data: print(f"[stderr] {data}"),
    timeout=60
)
```

### 代码上下文隔离

```python
# 创建独立上下文
ctx = sandbox.create_code_context(language="python")

# 默认上下文
sandbox.run_code("x = 1")

# 独立上下文
sandbox.run_code("x = 2", context=ctx)

# 验证隔离
print(sandbox.run_code("print(x)").logs.stdout[0])           # 输出: 1
print(sandbox.run_code("print(x)", context=ctx).logs.stdout[0])  # 输出: 2
```

### 文件操作

```python
# 上传文件
with open("data.csv", "r") as f:
    sandbox.files.write("/home/user/data.csv", f)

# 下载文件
content = sandbox.files.read("/home/user/output.txt", format="bytes")
with open("output.txt", "wb") as f:
    f.write(content)

# 检查文件是否存在
exists = sandbox.files.exists("/home/user/data.csv")

# 列出目录
for item in sandbox.files.list("/home/user"):
    print(f"  {item.path} ({item.type})")

# 创建目录
sandbox.files.make_dir("/home/user/output")

# 删除文件
sandbox.files.remove("/home/user/temp.txt")
```

### 终端命令执行

```python
# 执行命令
result = sandbox.commands.run("pip install pandas && python -c 'import pandas; print(pandas.__version__)'")
print(result.stdout)

# 后台执行
handler = sandbox.commands.run("python long_task.py", background=True)

# 等待后台命令
response = handler.wait(
    on_stdout=lambda data: print(data, end=""),
    on_stderr=lambda data: print(data, end="")
)
print(f"退出码: {response.exit_code}")

# 向运行中的命令发送输入
sandbox.commands.send_stdin(handler.pid, "yes\n")

# 终止命令
sandbox.commands.kill(handler.pid)
```

### 沙箱管理

```python
# 列出所有沙箱
paginator = Sandbox.list(limit=10)
while paginator.has_next:
    for info in paginator.next_items():
        print(f"  {info.sandbox_id} | {info.template}")

# 连接到已有沙箱
sandbox2 = Sandbox.connect(sandbox.sandbox_id)

# 修改超时
sandbox.set_timeout(1800)  # 延长到 30 分钟

# 获取端口对应的公网地址
host = sandbox.get_host(8080)
print(f"访问地址: https://{host}")

# 终止沙箱
sandbox.kill()
```

### 自定义镜像（x-custom-config）

```python
import json

# 使用自定义镜像创建沙箱
custom_config = {
    "image": "your-registry.tencentcloudcr.com/ns/image:tag",
    "imageRegistryType": "enterprise",
    "command": ["/bin/sh", "-c"],
    "args": ["python3 /app/server.py"],
    "env": [
        {"name": "PORT", "value": "8080"},
        {"name": "DEBUG", "value": "true"}
    ],
    "ports": [
        {"name": "http", "port": 8080, "protocol": "TCP"}
    ],
    "resources": {
        "cpu": "2",
        "memory": "4Gi"
    },
    "probe": {
        "httpGet": {"path": "/health", "port": 8080, "scheme": "HTTP"},
        "readyTimeoutMs": 30000,
        "probeTimeoutMs": 1000,
        "probePeriodMs": 100,
        "successThreshold": 1,
        "failureThreshold": 100
    }
}

sandbox = Sandbox.create(
    template="code-interpreter-v1",
    metadata={"x-custom-config": json.dumps(custom_config)},
    timeout=3600
)
```

---

## 三、两种 SDK 对比

| 特性 | 云 API SDK | e2b SDK |
|------|-----------|---------|
| **包名** | `tencentcloud-sdk-python>=3.1.32` | `e2b_code_interpreter>=2.4.1` |
| **认证方式** | `TENCENTCLOUD_SECRET_ID/KEY` | `E2B_API_KEY` + `E2B_DOMAIN` |
| **API 端点** | `ags.tencentcloudapi.com` | `{region}.tencentags.com` |
| **适用场景** | 工具/实例管理、自定义镜像 | 代码执行、文件操作 |
| **抽象层级** | 低级（直接 API 调用） | 高级（面向开发者） |
| **工具类型** | 所有类型（custom, browser, code-interpreter, swe, mobile） | 主要用于 code-interpreter |

### 选择建议

- **需要自定义 Docker 镜像**：使用云 API SDK 创建 custom 类型工具
- **需要执行代码片段**：使用 e2b SDK（更简洁）
- **本项目方案**：云 API SDK 创建/管理工具和实例 + HTTP 直接访问沙箱

---

## 四、API 响应字段速查

### 云 API SDK 响应结构

| 接口 | 关键响应字段 |
|------|-------------|
| `CreateSandboxTool` | `resp.ToolId` |
| `DescribeSandboxToolList` | `resp.SandboxToolSet[]`、`resp.TotalCount` |
| `StartSandboxInstance` | `resp.Instance.InstanceId` |
| `DescribeSandboxInstanceList` | `resp.InstanceSet[]`、`resp.TotalCount` |
| `AcquireSandboxInstanceToken` | `resp.Token`、`resp.ExpiresAt` |
| `StopSandboxInstance` | `resp.RequestId` |
| `DeleteSandboxTool` | `resp.RequestId` |

### 沙箱实例状态机

```
CREATING → RUNNING → STOPPING → STOPPED
                  ↘ FAILED
```

### 沙箱工具状态机

```
CREATING → ACTIVE
         ↘ FAILED
```
