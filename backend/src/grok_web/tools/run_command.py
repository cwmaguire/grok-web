import asyncio

from grok_web.tools import ToolDefinition, ToolResult, ToolRegistry

DEFINITION = ToolDefinition(
    name="run_command",
    description="Execute a shell command and return its output. Use for git, build tools, running scripts, etc. Commands run with a 120-second timeout.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command. Optional.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 120, max 600)",
            },
        },
        "required": ["command"],
    },
)


async def handle(command: str, cwd: str | None = None, timeout: int = 120) -> ToolResult:
    timeout = min(max(timeout, 1), 600)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(
                output=f"Command timed out after {timeout}s",
                is_error=True,
            )

        output_parts = []
        if stdout:
            output_parts.append(stdout.decode("utf-8", errors="replace"))
        if stderr:
            output_parts.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")

        output = "\n".join(output_parts) if output_parts else "(no output)"

        # Truncate very long output
        if len(output) > 50000:
            output = output[:50000] + "\n... (output truncated)"

        if proc.returncode != 0:
            output = f"Exit code: {proc.returncode}\n{output}"

        return ToolResult(
            output=output,
            is_error=proc.returncode != 0,
        )
    except Exception as e:
        return ToolResult(output=f"Error running command: {e}", is_error=True)


def register(registry: ToolRegistry):
    registry.register(DEFINITION, handle)
