# TerminalBench-AGS

基于腾讯云 AGS（Agent Sandbox Service）运行 Terminal Bench 评测的完整示例。LLM Agent（kimi-k2.5）在云端沙箱中自主完成终端任务，并自动验证结果。

## 概述

本项目演示如何使用腾讯云 AGS 作为沙箱基础设施，运行 [Terminal Bench](https://github.com/harbor-framework/terminal-bench-2) 评测任务。示例任务为 **compile-compcert** —— 从源码编译 CompCert 验证型 C 编译器。

### 架构

```
┌──────────────────────┐     ┌──────────────────────────────┐     ┌──────────────────────┐
│   LLM Agent          │────▶│  AGS 沙箱                     │────▶│  验证器              │
│   (kimi-k2.5)        │◀────│  (自定义 Docker 镜像)          │     │  (pytest 验证)       │
└──────────────────────┘     └──────────────────────────────┘     └──────────────────────┘
```

- **Agent**：通过腾讯 TokenHub 调用 kimi-k2.5（OpenAI 兼容 API），使用 function calling
- **沙箱**：AGS 自定义沙箱工具，运行 ubuntu:24.04 + HTTP 命令执行服务
- **验证器**：上传 pytest 测试文件并验证 CompCert 编译结果

## 快速开始

### 前置条件

- Python 3.11+
- Docker（用于构建沙箱镜像）
- 腾讯云账号，已开通 AGS 服务
- TokenHub 访问权限（kimi-k2.5）

### 安装

```bash
# 安装 Python 依赖
make setup

# 设置环境变量
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"
export TENCENTCLOUD_REGION="ap-beijing"

# 构建并推送 Docker 镜像（首次使用）
make build-push
```

### 运行

```bash
make run
```

执行流程：
1. 创建 AGS 沙箱工具（或复用已有工具）
2. 启动沙箱实例
3. LLM Agent 执行编译任务
4. 运行 pytest 验证
5. 输出 PASS/FAIL 结果并清理

### 清理资源

```bash
make clean
```

## 运行效果

以下为实际执行记录（2026-05-08，ap-beijing）：

```
============================================================
Terminal Bench Demo - compile-compcert
Using Tencent Cloud AGS + kimi-k2.5
============================================================

[main] Step 1: Creating/finding sandbox tool...
[sandbox_manager] Found existing tool: sdt-bvlaarik       ← AGS 工具复用

[main] Step 2: Starting sandbox instance...
[sandbox_manager] Instance started: t67c4r5p...           ← 实例秒级启动

[main] Step 3: Waiting for instance to be ready...
[sandbox_manager] Instance status: RUNNING                ← 镜像已缓存，即时就绪

[main] Step 5: Connecting to sandbox...
[main] Sandbox health check passed                        ← HTTP 命令服务正常

[main] Step 6: Running agent...
[agent] Step 1/50 - uname -a                              ← 检测 x86_64 Ubuntu 24.04
[agent] Step 2/50 - mkdir -p /tmp/CompCert                ← 创建工作目录
[agent] Step 3/50 - wget CompCert-v3.13.1.tar.gz          ← 下载源码 (2.8MB)
[agent] Step 4/50 - tar -xzf v3.13.1.tar.gz              ← 解压成功
[agent] Step 5/50 - apt-get install ocaml coq menhir ...  ← 安装编译依赖
[agent] Step 6+   - ./configure && make                   ← 配置并编译 (15-25 min)

[main] Step 7: Running verifier...
[verifier] Reward: 1                                      ← 验证通过

============================================================
RESULT: PASS
============================================================
```

> 完整执行需要 20-40 分钟（主要耗时在 CompCert 编译）。详见 [执行记录](docs/execution-log.md)。

## 项目结构

```
.
├── README.md               # 项目说明
├── Dockerfile              # 沙箱容器镜像
├── Makefile                # 构建、推送、运行命令
├── requirements.txt        # Python 依赖
├── src/
│   ├── run_bench.py        # 主编排器
│   ├── agent.py            # LLM Agent（kimi-k2.5 + function calling）
│   ├── sandbox_manager.py  # AGS 控制面（创建工具、启停实例）
│   ├── sandbox_client.py   # HTTP 客户端（沙箱命令执行）
│   ├── cmd_server.py       # 容器内 HTTP 命令服务器
│   ├── verifier.py         # 测试验证运行器
│   └── tests/
│       ├── test_outputs.py     # pytest 验证套件
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

## 文档

- [架构设计](docs/architecture.md) — 系统架构与组件说明
- [使用指南](docs/usage.md) — 详细安装与操作步骤
- [AGS SDK 参考](docs/ags-sdk.md) — 完整的 AGS 云 API 和 e2b SDK 使用示例
- [执行记录](docs/execution-log.md) — 实际运行过程与性能观察
- [问题排查](docs/troubleshooting.md) — 常见问题与解决方案

## 参考资料

- [AGS Cookbook](https://github.com/TencentCloudAgentRuntime/ags-cookbook) — 腾讯云 AGS 官方示例
- [Terminal Bench](https://github.com/harbor-framework/terminal-bench-2) — Terminal Bench 评测框架

## License

MIT
