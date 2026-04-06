"""
Claude AI agent plugin.

Requires the ``anthropic`` package: pip install swan[claude]
"""
from __future__ import annotations

from typing import Any

from swan.plugins.base import AgentPlugin
from swan.core.models import Task


class Plugin(AgentPlugin):
    """Calls the Claude API to process a prompt.

    Required task input key:
        prompt (str): The user message to send to Claude.

    Optional task input keys:
        model (str):       Claude model ID (default from plugin config or claude-haiku-4-5-20251001).
        system (str):      System prompt.
        max_tokens (int):  Maximum tokens to generate (default: 1024).

    Plugin config keys (set via `swan agent add --config`):
        model (str):   Default model for this agent.
        api_key (str): Anthropic API key (or set ANTHROPIC_API_KEY env var).
    """

    plugin_type = "claude"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise ImportError(
                "The Claude plugin requires the 'anthropic' package. "
                "Install it with: pip install swan[claude]"
            )

    async def run(self, task: Task) -> dict[str, Any]:
        import anthropic

        prompt: str = task.input.get("prompt", "")
        if not prompt:
            raise ValueError("ClaudePlugin requires task.input['prompt']")

        model: str = task.input.get(
            "model",
            self.config.get("model", "claude-haiku-4-5-20251001"),
        )
        system: str | None = task.input.get("system") or self.config.get("system")
        max_tokens: int = int(task.input.get("max_tokens", self.config.get("max_tokens", 1024)))

        api_key: str | None = self.config.get("api_key")
        client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        message = await client.messages.create(**kwargs)
        content = message.content[0].text if message.content else ""

        return {
            "model": model,
            "content": content,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "stop_reason": message.stop_reason,
        }
