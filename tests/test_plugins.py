import pytest
from swan.core.models import Task
from swan.core.enums import TaskStatus
from datetime import datetime


def _task(input: dict) -> Task:
    return Task(
        id="t1", swarm_id="s1", agent_id="a1", name="test-task",
        input=input, timeout=10.0, retries=0, retry_delay=1.0,
        depends_on=[], created_at=datetime.utcnow(), status=TaskStatus.PENDING,
    )


@pytest.mark.asyncio
async def test_shell_plugin_echo():
    from swan.plugins.builtin.shell import Plugin
    plugin = Plugin({})
    result = await plugin.run(_task({"command": "echo hello"}))
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]


@pytest.mark.asyncio
async def test_shell_plugin_prompt_substitution():
    from swan.plugins.builtin.shell import Plugin
    plugin = Plugin({})
    result = await plugin.run(_task({"command": "echo {prompt}", "prompt": "world"}))
    assert "world" in result["stdout"]


@pytest.mark.asyncio
async def test_shell_plugin_nonzero_exit():
    from swan.plugins.builtin.shell import Plugin
    plugin = Plugin({})
    result = await plugin.run(_task({"command": "exit 42"}))
    assert result["exit_code"] == 42


@pytest.mark.asyncio
async def test_shell_plugin_missing_command():
    from swan.plugins.builtin.shell import Plugin
    plugin = Plugin({})
    with pytest.raises(ValueError, match="command"):
        await plugin.run(_task({}))


@pytest.mark.asyncio
async def test_http_plugin(httpserver):
    """Integration test using pytest-localserver or similar — skip if unavailable."""
    pytest.importorskip("werkzeug")
    from swan.plugins.builtin.http import Plugin
    httpserver.expect_request("/test").respond_with_json({"ok": True})
    plugin = Plugin({})
    result = await plugin.run(_task({"url": httpserver.url_for("/test")}))
    assert result["status_code"] == 200
    assert result["body"] == {"ok": True}


def test_plugin_registry_resolve():
    from swan.plugins.registry import PluginRegistry, UnknownPluginError
    from swan.plugins.builtin.shell import Plugin as ShellPlugin
    PluginRegistry.register(ShellPlugin)
    resolved = PluginRegistry.resolve("shell")
    assert resolved is ShellPlugin
    with pytest.raises(UnknownPluginError):
        PluginRegistry.resolve("nonexistent")
