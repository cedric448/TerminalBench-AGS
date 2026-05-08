"""
LLM Agent - Uses kimi-k2.5 via TokenHub to execute terminal commands.
Implements an agentic loop with function calling.
"""

import json
import time
from openai import OpenAI

from sandbox_client import SandboxClient


# Agent configuration
MAX_STEPS = 50
AGENT_TIMEOUT = 2400  # 40 minutes
COMMAND_TIMEOUT = 300  # 5 minutes per command

SYSTEM_PROMPT = """You are a terminal agent with access to a bash shell on an Ubuntu 24.04 system.
You can execute any bash command using the execute_command tool.
The system has python3, curl, wget, and git pre-installed. You need to install any other dependencies yourself.

Important guidelines:
- Install packages non-interactively (use -y flag for apt-get)
- Check command output for errors and fix them
- Work step by step, verifying each step before moving to the next
- When you are done with the task, respond with a message saying the task is complete (do NOT call any tool)
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a bash command in the terminal. Returns stdout, stderr, and exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    }
]


def create_llm_client():
    """Create the OpenAI-compatible client for kimi-k2.5."""
    return OpenAI(
        api_key="sk-64YbwBozyGUU6asqXy07rM7Qf6FIDuUzIGFtgWQqtwGmPfAe",
        base_url="https://tokenhub.tencentmaas.com/v1"
    )


def run_agent(sandbox: SandboxClient, instruction: str) -> bool:
    """
    Run the LLM agent to complete the given instruction.

    Args:
        sandbox: SandboxClient instance for command execution
        instruction: The task instruction for the agent

    Returns:
        True if agent completed successfully, False otherwise
    """
    client = create_llm_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task:\n{instruction}"}
    ]

    start_time = time.time()
    step = 0

    print(f"[agent] Starting agent with instruction: {instruction[:80]}...")

    while step < MAX_STEPS:
        elapsed = time.time() - start_time
        if elapsed > AGENT_TIMEOUT:
            print(f"[agent] Timeout after {elapsed:.0f}s")
            return False

        step += 1
        print(f"\n[agent] Step {step}/{MAX_STEPS} (elapsed: {elapsed:.0f}s)")

        try:
            response = client.chat.completions.create(
                model="kimi-k2.5",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except Exception as e:
            print(f"[agent] LLM API error: {e}")
            time.sleep(5)
            continue

        choice = response.choices[0]
        message = choice.message

        # Append assistant message to history
        messages.append(message.model_dump())

        # Check if agent is done (no tool calls)
        if not message.tool_calls:
            print(f"[agent] Agent finished: {message.content}")
            return True

        # Process tool calls
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            if func_name == "execute_command":
                command = func_args["command"]
                print(f"[agent] Executing: {command[:100]}{'...' if len(command) > 100 else ''}")

                try:
                    result = sandbox.exec_command(command, timeout=COMMAND_TIMEOUT)
                    stdout = result["stdout"]
                    stderr = result["stderr"]
                    exit_code = result["exit_code"]

                    # Truncate very long outputs
                    max_output = 8000
                    if len(stdout) > max_output:
                        stdout = stdout[:max_output] + "\n... [truncated]"
                    if len(stderr) > max_output:
                        stderr = stderr[:max_output] + "\n... [truncated]"

                    tool_output = f"Exit code: {exit_code}\n"
                    if stdout:
                        tool_output += f"STDOUT:\n{stdout}\n"
                    if stderr:
                        tool_output += f"STDERR:\n{stderr}\n"

                    print(f"[agent]   Exit code: {exit_code}")
                    if stdout:
                        print(f"[agent]   Stdout: {stdout[:200]}{'...' if len(stdout) > 200 else ''}")
                    if stderr:
                        print(f"[agent]   Stderr: {stderr[:200]}{'...' if len(stderr) > 200 else ''}")

                except Exception as e:
                    tool_output = f"Error executing command: {e}"
                    print(f"[agent]   Error: {e}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Unknown function: {func_name}"
                })

    print(f"[agent] Max steps ({MAX_STEPS}) reached")
    return False
