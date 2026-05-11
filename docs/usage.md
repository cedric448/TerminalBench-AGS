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

项目使用两个镜像：

```bash
# 登录 TCR
docker login lily-tcr.tencentcloudcr.com --username <用户名> --password <令牌>

# 构建基础镜像（包含 cmd_server + 测试文件）
docker build -t lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6 .
docker push lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6

# 构建任务镜像（用于 StorageVolume 挂载）
docker build -t lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench-task:v1 -f Dockerfile .
docker push lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench-task:v1
```

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
cd src && python3 -u run_bench.py
```

### 使用 sandbox_manager CLI

```bash
# 创建/查找工具
cd src && python3 sandbox_manager.py create

# 启动实例并获取 token
cd src && python3 sandbox_manager.py start

# 列出所有工具
cd src && python3 sandbox_manager.py list

# 停止所有实例
cd src && python3 sandbox_manager.py stop-all

# 清理（停止实例 + 删除工具）
cd src && python3 sandbox_manager.py cleanup
```

### 执行过程

1. **创建工具** — 创建 AGS 沙箱工具，配置基础镜像 + StorageVolume（已存在则跳过）
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
[sandbox_manager] Found existing tool: sdt-37khr366 (status: ACTIVE)

[main] Step 2: Starting sandbox instance...
[sandbox_manager] Instance started: <instance_id>

[main] Step 3: Waiting for instance to be ready...
[sandbox_manager] Instance ... status: RUNNING

[main] Step 6: Running agent...
[agent] Step 1/50 - uname -a (检测 x86_64 Ubuntu 24.04)
[agent] Step 2/50 - mkdir -p /tmp/CompCert
[agent] Step 3/50 - apt-get install ocaml coq menhir ... (安装依赖)
[agent] Step 4/50 - wget CompCert v3.13.1 源码
[agent] Step 5/50 - ./configure x86_64-linux
[agent] Step 6+   - make (编译 15-25 分钟)
...
[agent] Agent finished: Task is complete.

[main] Step 7: Running verifier...
[verifier] Reward: 1

============================================================
RESULT: PASS
Agent time: ~1200-1800s
Reward: 1
============================================================
```

> 完整执行约 20-40 分钟（主要耗时在 CompCert 编译）。

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

1. 修改 `instruction.md` 中的任务指令
2. 更新 `src/tests/` 中的验证测试文件
3. 重新构建并推送任务镜像

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
