import asyncio
import pytest
from datetime import datetime
from swan.core.enums import ResultStatus
from swan.core.executor import TaskExecutor
from swan.core.models import Task
from swan.plugins.base import AgentPlugin


class OkPlugin(AgentPlugin):
    plugin_type = "ok"
    async def run(self, task: Task):
        return {"result": "ok"}


class FailPlugin(AgentPlugin):
    plugin_type = "fail"
    async def run(self, task: Task):
        raise ValueError("intentional failure")


class SlowPlugin(AgentPlugin):
    plugin_type = "slow"
    async def run(self, task: Task):
        await asyncio.sleep(10)
        return "done"


def _make_task(**kwargs) -> Task:
    defaults = dict(
        id="t1", swarm_id="s1", agent_id="a1", name="test",
        input={}, timeout=5.0, retries=0, retry_delay=0.1, depends_on=[],
    )
    defaults.update(kwargs)
    from swan.core.enums import TaskStatus
    from datetime import datetime
    return Task(created_at=datetime.utcnow(), status=TaskStatus.PENDING, **defaults)


@pytest.mark.asyncio
async def test_executor_success():
    executor = TaskExecutor()
    task = _make_task()
    result = await executor.run_task(task, OkPlugin({}))
    assert result.status == ResultStatus.SUCCESS
    assert result.output == {"result": "ok"}
    assert result.error is None
    assert result.attempt == 0


@pytest.mark.asyncio
async def test_executor_failure():
    executor = TaskExecutor()
    task = _make_task()
    result = await executor.run_task(task, FailPlugin({}))
    assert result.status == ResultStatus.FAILURE
    assert "intentional failure" in result.error


@pytest.mark.asyncio
async def test_executor_timeout():
    executor = TaskExecutor()
    task = _make_task(timeout=0.05)
    result = await executor.run_task(task, SlowPlugin({}))
    assert result.status == ResultStatus.TIMEOUT
    assert "Timed out" in result.error


@pytest.mark.asyncio
async def test_executor_retry_then_success():
    call_count = 0

    class FlakyPlugin(AgentPlugin):
        plugin_type = "flaky"
        async def run(self, task: Task):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("not yet")
            return "finally"

    executor = TaskExecutor()
    task = _make_task(retries=3, retry_delay=0.01)
    result = await executor.run_task(task, FlakyPlugin({}))
    assert result.status == ResultStatus.SUCCESS
    assert result.output == "finally"
    assert result.attempt == 2
