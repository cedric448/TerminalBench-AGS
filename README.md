# TerminalBench-AGS

基于腾讯云 AGS（Agent Sandbox Service）运行 Terminal Bench 评测的完整示例。LLM Agent（kimi-k2.5）在云端沙箱中自主完成终端任务，并自动验证结果。

## 概述

本项目演示如何使用腾讯云 AGS 作为沙箱基础设施，运行 [Terminal Bench](https://github.com/harbor-framework/terminal-bench-2) 评测任务。示例任务为 **compile-compcert** —— 从源码编译 CompCert 验证型 C 编译器。

### 架构

```
┌──────────────────────┐     ┌────────────────────────────────────┐     ┌──────────────────────┐
│   LLM Agent          │────▶│  AGS 沙箱                           │────▶│  验证器              │
│   (kimi-k2.5)        │◀────│  Base Image + Task Volume Mount    │     │  (pytest 验证)       │
└──────────────────────┘     └────────────────────────────────────┘     └──────────────────────┘
```

- **Agent**：通过腾讯 TokenHub 调用 kimi-k2.5（OpenAI 兼容 API），使用 function calling
- **沙箱**：AGS 自定义沙箱工具，企业镜像运行 cmd_server + StorageVolume 挂载任务镜像
- **验证器**：运行 pytest 测试套件验证 CompCert 编译结果

### 双镜像设计

| 镜像 | 用途 | 挂载方式 |
|------|------|----------|
| `terminal-bench:v6` | 基础运行时（Ubuntu 24.04 + cmd_server） | 作为容器主镜像 |
| `terminal-bench-task:v1` | 评测内容（tests + instruction） | StorageVolume 挂载到 `/task` |

## 快速开始

### 前置条件

- Python 3.11+
- Docker（用于构建沙箱镜像）
- 腾讯云账号，已开通 AGS 服务
- TokenHub 访问权限（kimi-k2.5）

### 安装

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 设置环境变量
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-beijing"

# 构建并推送 Docker 镜像
docker build -t lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6 .
docker push lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6
```

### 运行

```bash
cd src && python3 -u run_bench.py
```

执行流程：
1. 创建 AGS 沙箱工具（配置基础镜像 + StorageVolume，已存在则跳过）
2. 启动沙箱实例
3. LLM Agent 执行编译任务（~20-40 分钟）
4. 运行 pytest 验证
5. 输出 PASS/FAIL 结果并清理

### CLI 工具

```bash
cd src
python3 sandbox_manager.py create    # 创建工具
python3 sandbox_manager.py start     # 启动实例
python3 sandbox_manager.py list      # 列出工具
python3 sandbox_manager.py stop-all  # 停止所有实例
python3 sandbox_manager.py cleanup   # 清理所有资源
```

## 项目结构

```
.
├── README.md               # 项目说明
├── Dockerfile              # 沙箱容器镜像（含 cmd_server + 测试文件）
├── instruction.md          # CompCert 编译任务指令
├── requirements.txt        # Python 依赖
├── src/
│   ├── run_bench.py        # 主编排器
│   ├── agent.py            # LLM Agent（kimi-k2.5 + function calling）
│   ├── sandbox_manager.py  # AGS 控制面（创建工具、StorageVolume、启停实例）
│   ├── sandbox_client.py   # HTTP 客户端（沙箱命令执行）
│   ├── cmd_server.py       # 容器内 HTTP 命令服务器
│   ├── verifier.py         # 测试验证运行器
│   └── tests/
│       ├── test_outputs.py     # pytest 验证套件
│       ├── test.sh             # 验证脚本（uv + pytest）
│       ├── positive_probe.c    # CompCert 编译测试
│       └── negative_probe.c    # VLA 拒绝测试
└── docs/
    ├── architecture.md     # 架构设计文档
    ├── usage.md            # 使用指南
    ├── ags-sdk.md          # AGS SDK 完整参考（云 API + e2b）
    ├── execution-log.md    # 执行记录与性能观察
    └── troubleshooting.md  # 问题排查
```

## 配置项

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `TENCENTCLOUD_SECRET_ID` | 腾讯云 SecretId | （必填） |
| `TENCENTCLOUD_SECRET_KEY` | 腾讯云 SecretKey | （必填） |
| `TENCENTCLOUD_REGION` | AGS 地域 | `ap-beijing` |

## AGS 工具配置

| 参数 | 值 |
|------|---|
| 工具名称 | `tb-compcert-v6` |
| 基础镜像 | `lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6` |
| 任务镜像（卷） | `lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench-task:v1` |
| 镜像类型 | enterprise |
| 卷挂载路径 | `/task` |
| 资源 | 2 CPU, 4Gi Memory |
| 网络 | PUBLIC |
| 健康探针 | HTTP GET /health:8080 |
| 超时 | 40 分钟 |

## 文档

- [架构设计](docs/architecture.md) — 系统架构、双镜像设计与 StorageVolume 说明
- [使用指南](docs/usage.md) — 详细安装与操作步骤
- [AGS SDK 参考](docs/ags-sdk.md) — 完整的 AGS 云 API 使用示例
- [e2b SDK 指南](docs/e2b-sdk.md) — e2b SDK + x-custom-config 动态镜像覆盖
- [执行记录](docs/execution-log.md) — 实际运行过程与性能观察
- [问题排查](docs/troubleshooting.md) — 常见问题与解决方案

## 参考资料

- [AGS Cookbook](https://github.com/TencentCloudAgentRuntime/ags-cookbook) — 腾讯云 AGS 官方示例
- [Terminal Bench](https://github.com/harbor-framework/terminal-bench-2) — Terminal Bench 评测框架

## License

MIT
