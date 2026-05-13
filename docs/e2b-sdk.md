# e2b SDK 使用指南

## 概述

AGS 提供了兼容 [e2b](https://e2b.dev/) 的 SDK 接口，可以通过 `e2b-code-interpreter` Python 包创建和管理沙箱实例。核心特性是 `x-custom-config`，允许在创建实例时动态覆盖 Tool 的镜像、命令、资源等配置。

## 安装

```bash
pip install e2b-code-interpreter
```

## 环境变量

```bash
export E2B_API_KEY="your-ags-api-key"       # AGS 控制台获取
export E2B_DOMAIN="ap-beijing.tencentags.com"  # AGS 地域域名
```

## 基本用法

### 创建沙箱（使用 Tool 默认配置）

```python
from e2b_code_interpreter import Sandbox

sandbox = Sandbox.create(
    template="sdt-r4f4evm2",  # Tool ID
    timeout=600               # 超时（秒）
)

print(f"Sandbox ID: {sandbox.sandbox_id}")
print(f"Host: {sandbox.get_host(8080)}")

# 清理
sandbox.kill()
```

### 使用 x-custom-config 覆盖镜像

通过 `metadata` 中的 `x-custom-config` 字段动态指定运行镜像，无需重新创建 Tool：

```python
import json
from e2b_code_interpreter import Sandbox

custom_config = {
    "image": "lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6",
    "imageRegistryType": "enterprise"
}

sandbox = Sandbox.create(
    template="sdt-r4f4evm2",
    timeout=600,
    metadata={
        "x-custom-config": json.dumps(custom_config)
    }
)
```

## x-custom-config 完整字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `image` | string | 镜像地址 |
| `imageRegistryType` | string | `enterprise` / `personal` / `system` |
| `command` | string[] | 启动命令 |
| `args` | string[] | 启动参数 |
| `env` | object[] | 环境变量 `[{"name": "KEY", "value": "VAL"}]` |
| `ports` | object[] | 端口声明 `[{"name": "http", "port": 8080, "protocol": "TCP"}]` |
| `resources` | object | 资源配置 `{"cpu": "2", "memory": "4Gi"}` |
| `probe` | object | 健康检查配置 |

### 综合配置示例

```python
full_config = {
    "image": "lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v7",
    "imageRegistryType": "enterprise",
    "command": ["python3"],
    "args": ["/cmd_server.py"],
    "env": [
        {"name": "DEBIAN_FRONTEND", "value": "noninteractive"}
    ],
    "ports": [
        {"name": "http", "port": 8080, "protocol": "TCP"}
    ],
    "resources": {
        "cpu": "2",
        "memory": "4Gi"
    },
    "probe": {
        "httpGet": {
            "path": "/health",
            "port": 8080,
            "scheme": "HTTP"
        },
        "readyTimeoutMs": 30000,
        "probeTimeoutMs": 2000,
        "probePeriodMs": 500,
        "successThreshold": 1,
        "failureThreshold": 100
    }
}

sandbox = Sandbox.create(
    template="sdt-r4f4evm2",
    timeout=600,
    metadata={
        "x-custom-config": json.dumps(full_config)
    }
)
```

## 与 cmd_server 通信

由于我们的自定义镜像使用 `cmd_server.py`（非 envd），需要通过 HTTP + Access Token 通信：

```python
import json
import requests
from e2b_code_interpreter import Sandbox
from tencentcloud.ags.v20250920 import ags_client, models
from tencentcloud.common import credential

# 1. 创建沙箱
sandbox = Sandbox.create(
    template="sdt-r4f4evm2",
    timeout=600,
    metadata={
        "x-custom-config": json.dumps({
            "image": "lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v7",
            "imageRegistryType": "enterprise"
        })
    }
)

instance_id = sandbox.sandbox_id
host = sandbox.get_host(8080)

# 2. 获取 Access Token（通过云 API）
cred = credential.Credential(
    os.environ["TENCENTCLOUD_SECRET_ID"],
    os.environ["TENCENTCLOUD_SECRET_KEY"]
)
client = ags_client.AgsClient(cred, "ap-beijing")
req = models.AcquireSandboxInstanceTokenRequest()
req.InstanceId = instance_id
token = client.AcquireSandboxInstanceToken(req).Token

# 3. 执行命令
base_url = f"https://{host}"
headers = {"X-Access-Token": token, "Content-Type": "application/json"}

resp = requests.post(
    f"{base_url}/exec",
    headers=headers,
    json={"command": "echo hello world"}
)
print(resp.json())
# {"stdout": "hello world\n", "stderr": "", "exit_code": 0}

# 4. 清理
sandbox.kill()
```

## 实际验证示例

以下为实际运行输出（2026-05-13）：

```
Template: sdt-r4f4evm2
x-custom-config image override: terminal-bench:v6

Sandbox created! ID: rnsqzc3plbn7o37jxusdbl4eebnstlypuzfm45vr
Host: 8080-rnsqzc3plbn7o37jxusdbl4eebnstlypuzfm45vr.ap-beijing.tencentags.com

=== Health Check ===
Status: 200, Body: {'status': 'ok'}

=== echo hello ===
stdout: hello
PRETTY_NAME="Ubuntu 24.04.4 LTS"
NAME="Ubuntu"

=== 验证使用的是 v6 镜像 (无 v2ray) ===
ls: cannot access '/usr/local/bin/v2ray': No such file or directory
---
negative_probe.c
positive_probe.c
test.sh
test_outputs.py
```

## 获取端口访问地址

```python
# 获取各端口的公网访问地址
host_8080 = sandbox.get_host(8080)   # cmd_server
host_49983 = sandbox.get_host(49983)  # envd (如果有)

# 格式: {port}-{sandbox_id}.{region}.tencentags.com
```

## 列出沙箱

```python
from e2b_code_interpreter import Sandbox

paginator = Sandbox.list(limit=10)
for info in paginator.next_items():
    print(f"ID: {info.sandbox_id}, Started: {info.started_at}")
```

## 注意事项

1. **x-custom-config 是 JSON 字符串** — 必须使用 `json.dumps()` 序列化
2. **镜像覆盖** — `x-custom-config` 中的 `image` 会覆盖 Tool 默认镜像，适合同一 Tool 运行不同版本
3. **认证方式** — e2b SDK 创建实例后，HTTP 访问需要通过云 API 获取 Access Token
4. **envd vs cmd_server** — e2b 的 `sandbox.commands.run()` 需要容器内有 envd；自定义镜像使用 cmd_server 时需通过 HTTP 直接调用
5. **VPC 模式** — VPC 网络需要绑定 NAT 网关才能访问外网

## 参考

- [AGS Cookbook - e2b custom](https://github.com/TencentCloudAgentRuntime/ags-cookbook/blob/main/tutorials/sdk/e2b/e2b_custom.ipynb)
- [e2b 官方文档](https://e2b.dev/docs)
