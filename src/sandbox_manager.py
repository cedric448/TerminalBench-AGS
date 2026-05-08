"""
AGS Sandbox Manager - Control plane operations for Tencent Cloud AGS.
Handles sandbox tool creation, instance lifecycle, and access token management.
"""

import os
import json
import time

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ags.v20250920 import ags_client, models


# Configuration
REGION = os.environ.get("TENCENTCLOUD_REGION", "ap-beijing")
TOOL_NAME = "terminal-bench-compcert"
IMAGE = "lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest"
IMAGE_REGISTRY_TYPE = "enterprise"
ROLE_ARN = "qcs::cam::uin/100008634787:roleName/ags-tcr-full"
DEFAULT_TIMEOUT = "40m"
INSTANCE_TIMEOUT = "40m"


def get_client():
    """Create an authenticated AGS client."""
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    http_profile = HttpProfile()
    http_profile.endpoint = "ags.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return ags_client.AgsClient(cred, REGION, client_profile)


def create_sandbox_tool(client):
    """Create a custom sandbox tool with the Terminal Bench image."""
    req = models.CreateSandboxToolRequest()
    req.ToolName = TOOL_NAME
    req.ToolType = "custom"
    req.Description = "Terminal Bench compile-compcert sandbox"
    req.DefaultTimeout = DEFAULT_TIMEOUT
    req.RoleArn = ROLE_ARN

    # Custom image configuration
    custom_config = models.CustomConfiguration()
    custom_config.Image = IMAGE
    custom_config.ImageRegistryType = IMAGE_REGISTRY_TYPE
    custom_config.Command = ["python3"]
    custom_config.Args = ["/cmd_server.py"]
    custom_config.Ports = [models.PortConfiguration()]
    custom_config.Ports[0].Name = "http"
    custom_config.Ports[0].Port = 8080
    custom_config.Ports[0].Protocol = "TCP"

    # Environment variables
    env_vars = []
    for name, value in [
        ("DEBIAN_FRONTEND", "noninteractive"),
        ("LANG", "en_US.UTF-8"),
        ("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
    ]:
        env_var = models.EnvVar()
        env_var.Name = name
        env_var.Value = value
        env_vars.append(env_var)
    custom_config.Env = env_vars

    # Resources
    resource_config = models.ResourceConfiguration()
    resource_config.CPU = "2"
    resource_config.Memory = "4Gi"
    custom_config.Resources = resource_config

    # Health probe (required for custom tools)
    probe_config = models.ProbeConfiguration()
    http_get = models.HttpGetAction()
    http_get.Path = "/health"
    http_get.Port = 8080
    http_get.Scheme = "HTTP"
    probe_config.HttpGet = http_get
    probe_config.ReadyTimeoutMs = 30000
    probe_config.ProbeTimeoutMs = 2000
    probe_config.ProbePeriodMs = 500
    probe_config.SuccessThreshold = 1
    probe_config.FailureThreshold = 100
    custom_config.Probe = probe_config

    req.CustomConfiguration = custom_config

    # Network - public access needed for downloading sources
    network_config = models.NetworkConfiguration()
    network_config.NetworkMode = "PUBLIC"
    req.NetworkConfiguration = network_config

    resp = client.CreateSandboxTool(req)
    print(f"[sandbox_manager] Tool created: {resp.ToolId}")
    return resp.ToolId


def find_existing_tool(client):
    """Find an existing tool by name."""
    try:
        req = models.DescribeSandboxToolListRequest()
        req.Limit = 100
        req.Offset = 0
        resp = client.DescribeSandboxToolList(req)
        if resp.SandboxToolSet:
            for tool in resp.SandboxToolSet:
                if tool.ToolName == TOOL_NAME:
                    print(f"[sandbox_manager] Found existing tool: {tool.ToolId}")
                    return tool.ToolId
    except TencentCloudSDKException as e:
        print(f"[sandbox_manager] Error listing tools: {e}")
    return None


def create_or_get_tool():
    """Create a new tool or return existing one."""
    client = get_client()
    tool_id = find_existing_tool(client)
    if tool_id:
        return tool_id
    tool_id = create_sandbox_tool(client)
    # Wait for tool to become ACTIVE
    wait_for_tool_active(tool_id)
    return tool_id


def wait_for_tool_active(tool_id, timeout=60):
    """Wait for a tool to become ACTIVE status."""
    client = get_client()
    start_time = time.time()
    while time.time() - start_time < timeout:
        req = models.DescribeSandboxToolListRequest()
        req.ToolIds = [tool_id]
        req.Limit = 1
        req.Offset = 0
        resp = client.DescribeSandboxToolList(req)
        if resp.SandboxToolSet:
            status = resp.SandboxToolSet[0].Status
            print(f"[sandbox_manager] Tool {tool_id} status: {status}")
            if status == "ACTIVE":
                return True
            elif status in ("FAILED",):
                raise RuntimeError(f"Tool creation failed: {status}")
        time.sleep(3)
    raise TimeoutError(f"Tool {tool_id} not active after {timeout}s")


def start_instance(tool_id):
    """Start a sandbox instance from the given tool."""
    client = get_client()
    req = models.StartSandboxInstanceRequest()
    req.ToolId = tool_id
    req.Timeout = INSTANCE_TIMEOUT

    resp = client.StartSandboxInstance(req)
    instance_id = resp.Instance.InstanceId
    print(f"[sandbox_manager] Instance started: {instance_id}")
    return instance_id


def wait_for_ready(instance_id, timeout=120):
    """Wait for instance to reach RUNNING status."""
    client = get_client()
    start_time = time.time()
    while time.time() - start_time < timeout:
        req = models.DescribeSandboxInstanceListRequest()
        req.Limit = 100
        req.Offset = 0
        resp = client.DescribeSandboxInstanceList(req)
        if resp.InstanceSet:
            for inst in resp.InstanceSet:
                if inst.InstanceId == instance_id:
                    status = inst.Status
                    print(f"[sandbox_manager] Instance {instance_id[:16]}... status: {status}")
                    if status == "RUNNING":
                        return True
                    elif status in ("FAILED", "STOPPED"):
                        reason = inst.StopReason if inst.StopReason else "unknown"
                        raise RuntimeError(f"Instance failed with status: {status}, reason: {reason}")
                    break
            else:
                print(f"[sandbox_manager] Instance {instance_id[:16]}... not in list yet")
        time.sleep(5)
    raise TimeoutError(f"Instance {instance_id} not ready after {timeout}s")


def get_access_token(instance_id):
    """Acquire access token for an instance."""
    client = get_client()
    req = models.AcquireSandboxInstanceTokenRequest()
    req.InstanceId = instance_id
    resp = client.AcquireSandboxInstanceToken(req)
    print(f"[sandbox_manager] Access token acquired for {instance_id}")
    return resp.Token


def stop_instance(instance_id):
    """Stop a running instance."""
    client = get_client()
    try:
        req = models.StopSandboxInstanceRequest()
        req.InstanceId = instance_id
        client.StopSandboxInstance(req)
        print(f"[sandbox_manager] Instance stopped: {instance_id}")
    except TencentCloudSDKException as e:
        print(f"[sandbox_manager] Error stopping instance: {e}")


def delete_tool(tool_id):
    """Delete a sandbox tool."""
    client = get_client()
    try:
        req = models.DeleteSandboxToolRequest()
        req.ToolId = tool_id
        client.DeleteSandboxTool(req)
        print(f"[sandbox_manager] Tool deleted: {tool_id}")
    except TencentCloudSDKException as e:
        print(f"[sandbox_manager] Error deleting tool: {e}")


def cleanup():
    """Full cleanup: stop all instances and delete tool."""
    client = get_client()
    tool_id = find_existing_tool(client)
    if not tool_id:
        print("[sandbox_manager] No tool found to clean up")
        return

    # Stop running instances
    req = models.DescribeSandboxInstanceListRequest()
    req.ToolId = tool_id
    req.Limit = 100
    req.Offset = 0
    try:
        resp = client.DescribeSandboxInstanceList(req)
        if resp.InstanceSet:
            for inst in resp.InstanceSet:
                if inst.Status == "RUNNING":
                    stop_instance(inst.InstanceId)
    except TencentCloudSDKException:
        pass

    # Delete tool
    delete_tool(tool_id)
    print("[sandbox_manager] Cleanup complete")
