from __future__ import annotations

import asyncio
import os
from asyncio.subprocess import PIPE
from typing import Any

from swan.plugins.base import AgentPlugin
from swan.core.models import Task


class Plugin(AgentPlugin):
    """Runs an arbitrary shell command.

    Required task input key:
        command (str): The shell command to execute. Supports ``{prompt}``
                       template substitution from task input.

    Optional task input keys:
        env (dict[str, str]): Extra environment variables merged with os.environ.
        stdin (str): Data to pipe to the process stdin.
    """

    plugin_type = "shell"

    async def run(self, task: Task) -> dict[str, Any]:
        cmd: str = task.input.get("command") or self.config.get("command", "")
        if not cmd:
            raise ValueError("ShellPlugin requires 'command' in task input or agent config")

        # Simple template substitution: {prompt} → task.input["prompt"]
        prompt = task.input.get("prompt", "")
        cmd = cmd.replace("{prompt}", prompt)

        env = {**os.environ, **task.input.get("env", {})}
        stdin_data: str | None = task.input.get("stdin")

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE if stdin_data is not None else None,
            env=env,
        )

        stdin_bytes = stdin_data.encode() if stdin_data is not None else None
        stdout_bytes, stderr_bytes = await proc.communicate(input=stdin_bytes)

        return {
            "exit_code": proc.returncode,
            "stdout": stdout_bytes.decode(errors="replace"),
            "stderr": stderr_bytes.decode(errors="replace"),
        }
