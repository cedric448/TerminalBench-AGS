# 使用指南

## 前置条件

1. **Python 3.11+**（含 pip）
2. **Docker**（已安装并运行）
3. **腾讯云账号**，需要：
   - ap-beijing 地域已开通 AGS 服务
   - 具有 AGS 权限的 SecretId/SecretKey
   - TCR（腾讯容器镜像服务）实例用于存储自定义镜像
   - CAM 角色允许 AGS 从 TCR 拉取镜像
4. **TokenHub 访问权限**（kimi-k2.5 模型）

## 初始安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

安装内容：
- `tencentcloud-sdk-python>=3.1.32` — AGS 控制面 SDK
- `openai>=1.0.0` — LLM API 客户端（OpenAI 兼容）
- `requests` — HTTP 客户端

### 2. 配置环境变量

```bash
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-beijing"
```

### 3. 构建并推送 Docker 镜像

首次使用（或更新沙箱镜像时）：

```bash
# 登录 TCR
docker login lily-tcr.tencentcloudcr.com --username <用户名> --password <令牌>

# 构建镜像
make build

# 推送到仓库
make push
```

Dockerfile 创建了一个最小化的 ubuntu:24.04 镜像，包含 python3、curl、wget、git 和命令执行服务。

### 4. TCR 命名空间

确保 TCR 仓库中存在 `terminalbench` 命名空间。如不存在，通过 TCR 控制台创建。

### 5. CAM 角色配置

AGS 需要一个角色来拉取 TCR 中的镜像。在 `src/sandbox_manager.py` 中配置角色 ARN：

```python
ROLE_ARN = "qcs::cam::uin/<your_uin>:roleName/<your_role>"
```

## 运行 Benchmark

### 完整运行

```bash
make run
```

或直接：

```bash
cd src && python run_bench.py
```

### 执行过程

1. **创建工具** — 创建 AGS 沙箱工具（已存在则跳过）
2. **启动实例** — 从工具启动沙箱容器
3. **等待就绪** — 轮询直到实例 RUNNING 且健康检查通过
4. **Agent 执行** — LLM Agent 接收任务指令并开始执行命令
5. **验证** — 上传测试文件并运行 pytest 验证编译结果
6. **清理** — 停止沙箱实例

### 预期输出

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
（Agent 执行约 15-30 步，耗时 15-40 分钟）
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

### 清理资源

```bash
make clean
```

停止所有运行中的实例并删除沙箱工具。

## 自定义配置

### 更换 LLM 模型

编辑 `src/agent.py`：

```python
client = OpenAI(
    api_key="your_api_key",
    base_url="your_base_url"
)
# 在 create 调用中：
model="your-model-name"
```

### 更换任务

编辑 `src/run_bench.py` 中的 `INSTRUCTION` 变量：

```python
INSTRUCTION = """你的自定义任务指令"""
```

### 调整超时

在 `src/agent.py` 中：
- `MAX_STEPS = 50` — 最大 Agent 迭代次数
- `AGENT_TIMEOUT = 2400` — Agent 总超时（秒）
- `COMMAND_TIMEOUT = 300` — 单条命令超时（秒）

### 调整沙箱资源

在 `src/sandbox_manager.py` 中：
```python
resource_config.CPU = "4"       # CPU 核数
resource_config.Memory = "8Gi"  # 内存
```
