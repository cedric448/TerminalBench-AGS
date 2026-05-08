# 执行记录

本文档记录了 TerminalBench-AGS Demo 的实际运行过程和结果。

## 环境信息

- **运行日期**: 2026-05-08
- **地域**: ap-beijing
- **LLM 模型**: kimi-k2.5 (via TokenHub)
- **沙箱镜像**: `lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest`
- **沙箱规格**: 2 CPU, 4Gi Memory, PUBLIC 网络
- **任务**: compile-compcert (编译 CompCert v3.13.1)

## 执行流程

### 1. 基础设施搭建

```
1. Docker 镜像构建 (ubuntu:24.04 + python3/curl/wget/git + cmd_server.py)
2. 镜像推送到 TCR: lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest
3. AGS 沙箱工具创建: sdt-bvlaarik (custom 类型, 健康探针 /health:8080)
```

### 2. Benchmark 启动

```
[main] Step 1: Creating/finding sandbox tool...
[sandbox_manager] Found existing tool: sdt-bvlaarik

[main] Step 2: Starting sandbox instance...
[sandbox_manager] Instance started: t67c4r5p6hq7pu5icc74akj5v4mdch3gtxpcnm6r

[main] Step 3: Waiting for instance to be ready...
[sandbox_manager] Instance status: RUNNING (首次查询即就绪，镜像已缓存)

[main] Step 4: Acquiring access token... ✅
[main] Step 5: Connecting to sandbox... health check passed ✅
```

### 3. Agent 执行过程

| Step | 耗时 | 命令 | 结果 |
|------|------|------|------|
| 1 | 0s | `uname -a && cat /etc/os-release` | ✅ Ubuntu 24.04, x86_64 |
| 2 | 8s | `mkdir -p /tmp/CompCert` | ✅ 目录创建成功 |
| 3 | 13s | `wget CompCert-v3.13.1.tar.gz` | ✅ 源码下载成功 (2.8MB) |
| 4 | 48s | `tar -xzf v3.13.1.tar.gz` | ✅ 解压成功, CompCert-3.13.1/ |
| 5 | 57s | `apt-get install ocaml coq menhir gcc make` | ⏳ 安装中 (预计3-5分钟) |
| 6+ | ... | `./configure x86_64-linux` | (后续步骤) |
| ... | ... | `make -j2` | (编译 ~15-25 分钟) |

### 4. Agent 决策分析

kimi-k2.5 表现出良好的任务规划能力：
- 正确识别了目标架构 (x86_64)
- 知道需要从 GitHub 下载 CompCert 源码
- 选择了正确的版本 (v3.13.1)
- 知道需要安装 OCaml/Coq/Menhir 依赖

### 5. 已验证功能

| 功能 | 状态 | 说明 |
|------|------|------|
| AGS 工具创建 | ✅ | 自定义镜像 + 健康探针 + 资源配置 |
| AGS 实例启动 | ✅ | 从工具启动，秒级就绪（镜像缓存后） |
| 访问令牌获取 | ✅ | Token 正常获取 |
| HTTP 命令执行 | ✅ | POST /exec 正常工作 |
| LLM Function Calling | ✅ | kimi-k2.5 tool_call 正常 |
| 命令输出回传 | ✅ | stdout/stderr/exit_code 完整返回 |
| Agent 循环 | ✅ | 多步骤连续执行 |

## 限制说明

当前 Demo 环境 (CodeBuddy) 有 120 秒 bash 执行超时限制，无法在该环境中观察完整的 30-40 分钟编译过程。完整运行需要在本地终端执行：

```bash
export TENCENTCLOUD_SECRET_ID="<your_id>"
export TENCENTCLOUD_SECRET_KEY="<your_key>"
export TENCENTCLOUD_REGION="ap-beijing"
cd src && python3 -u run_bench.py
```

## AGS 性能观察

| 指标 | 值 |
|------|---|
| 工具创建耗时 | ~3s |
| 实例启动耗时（首次） | ~5-10s |
| 实例启动耗时（镜像缓存） | <3s |
| 健康检查通过 | 即时 |
| 令牌获取 | <1s |
| 命令执行延迟 | ~100-300ms (网络往返) |
| LLM 响应时间 | ~5-15s (kimi-k2.5) |
