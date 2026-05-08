# 架构设计

## 系统总览

TerminalBench-AGS 是一个端到端的 Benchmark 运行器，使用腾讯云 AGS（Agent Sandbox Service）作为执行环境，评估 LLM Agent 在终端任务上的表现。

```
┌─────────────────────────────────────────────────────────────────────┐
│                          宿主机                                       │
│                                                                       │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐ │
│  │ run_bench.py│───▶│sandbox_mgr.py│───▶│ AGS 控制面 API          │ │
│  │ 编排器      │    │              │    │ (ags.tencentcloudapi.com)│ │
│  └──────┬──────┘    └──────────────┘    └─────────────────────────┘ │
│         │                                                             │
│         ▼                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐ │
│  │  agent.py   │───▶│sandbox_cli.py│───▶│ AGS 数据面 (HTTP)       │ │
│  │ LLM Agent   │    │ HTTP 客户端  │    │ 8080-{id}.{r}.tencentags│ │
│  └──────┬──────┘    └──────────────┘    └────────────┬────────────┘ │
│         │                                             │               │
│         ▼                                             ▼               │
│  ┌─────────────┐                        ┌─────────────────────────┐ │
│  │ verifier.py │                        │   AGS 沙箱实例           │ │
│  │ 验证器      │                        │  ┌───────────────────┐  │ │
│  └─────────────┘                        │  │  cmd_server.py    │  │ │
│                                          │  │  (端口 8080)      │  │ │
│                                          │  │  GET /health      │  │ │
│                                          │  │  POST /exec       │  │ │
│                                          │  │  POST /upload     │  │ │
│                                          │  │  GET /download    │  │ │
│                                          │  └───────────────────┘  │ │
│                                          └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 编排器 (`run_bench.py`)

主入口，协调整个 Benchmark 生命周期：
1. 创建/查找 AGS 沙箱工具
2. 启动沙箱实例并等待就绪
3. 获取访问令牌
4. 运行 LLM Agent
5. 运行验证测试
6. 输出结果并清理

### 2. 沙箱管理器 (`sandbox_manager.py`)

通过 `tencentcloud-sdk-python` 操作 AGS 控制面：

- **CreateSandboxTool** — 注册自定义沙箱工具（Docker 镜像、健康探针、资源配置）
- **StartSandboxInstance** — 从工具启动沙箱实例
- **DescribeSandboxInstanceList** — 轮询实例状态直到 RUNNING
- **AcquireSandboxInstanceToken** — 获取 HTTP 访问令牌
- **StopSandboxInstance** — 停止并清理实例
- **DeleteSandboxTool** — 删除工具定义

### 3. 沙箱客户端 (`sandbox_client.py`)

HTTP 客户端，与容器内的 `cmd_server.py` 通信：

- `exec_command(cmd)` — 执行 bash 命令，返回 stdout/stderr/exit_code
- `upload_file(local, remote)` — 上传文件到沙箱（base64 编码）
- `download_file(remote)` — 从沙箱下载文件
- `health_check()` — 验证沙箱是否响应

### 4. 命令服务器 (`cmd_server.py`)

运行在 Docker 容器内的最小化 HTTP 服务器（仅使用 Python 标准库）：

| 端点 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | AGS 就绪探针 |
| `/exec` | POST | 执行 shell 命令 |
| `/upload` | POST | 上传文件（base64） |
| `/download` | GET | 下载文件 |

### 5. LLM Agent (`agent.py`)

使用 kimi-k2.5（通过 TokenHub OpenAI 兼容 API）的 Agent 循环：

- 系统提示词指导 Agent 完成终端任务
- 单一工具：`execute_command(command: str)`
- 循环：LLM 生成 tool_call → 在沙箱执行 → 返回结果 → 重复
- 终止条件：LLM 不再调用工具 或 达到最大步数
- 超时：2400s（40 分钟），最大步数：50

### 6. 验证器 (`verifier.py`)

Agent 完成后运行验证：
1. 上传测试文件到沙箱
2. 通过 uv 安装 pytest
3. 运行测试套件检查 CompCert 安装
4. 返回奖励值：1（通过）或 0（失败）

## 数据流

```
1. 编排器创建 AGS 工具（一次性）
2. 编排器启动实例 → AGS 拉取 Docker 镜像 → 容器启动
3. AGS 健康探针访问 cmd_server /health → 实例标记为 RUNNING
4. Agent 调用 kimi-k2.5 API → 获取 tool_call → sandbox_client POST 到 /exec
5. cmd_server 执行 bash 命令 → 返回 JSON 响应
6. Agent 循环继续直到任务完成
7. 验证器上传测试 → 运行 pytest → 收集奖励
8. 编排器停止实例
```

## AGS 配置参数

| 参数 | 值 |
|------|---|
| 工具名称 | `terminal-bench-compcert` |
| 镜像 | `lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest` |
| 镜像仓库类型 | enterprise |
| 资源 | 2 CPU, 4Gi 内存 |
| 网络 | PUBLIC（需要公网下载源码） |
| 探针 | HTTP GET /health:8080 |
| 超时 | 40 分钟 |
| RoleArn | `qcs::cam::uin/100008634787:roleName/ags-tcr-full` |

## 安全说明

- 沙箱具有公网访问权限（需要下载 CompCert 源码）
- 每条命令有独立超时（默认 300s）
- 容器以 root 运行（apt-get 需要）
- 沙箱访问需要 AGS 颁发的限时令牌
