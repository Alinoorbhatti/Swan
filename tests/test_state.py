import pytest
from datetime import datetime
from swan.core.models import Agent, Swarm, Task, TaskResult
from swan.core.enums import ResultStatus
from swan.state.base import StateRoot


@pytest.mark.asyncio
async def test_store_roundtrip(store):
    state = await store.load()
    swarm = Swarm.create("test-swarm")
    state.swarms[swarm.id] = swarm
    await store.save(state)

    store.invalidate_cache()
    state2 = await store.load()
    assert swarm.id in state2.swarms
    assert state2.swarms[swarm.id].name == "test-swarm"


@pytest.mark.asyncio
async def test_store_save_result(store):
    now = datetime.utcnow()
    result = TaskResult(
        task_id="t1", agent_id="a1", swarm_id="s1",
        status=ResultStatus.SUCCESS, output="done",
        error=None, started_at=now, finished_at=now, duration_ms=10, attempt=0,
    )
    await store.save_result(result)
    store.invalidate_cache()
    results = await store.get_results("t1")
    assert len(results) == 1
    assert results[0].output == "done"


@pytest.mark.asyncio
async def test_atomic_write_does_not_corrupt(store, tmp_path):
    """File should exist and be valid JSON after save."""
    state = await store.load()
    swarm = Swarm.create("atomic-test")
    state.swarms[swarm.id] = swarm
    await store.save(state)

    import json
    with open(store._path) as fh:
        data = json.load(fh)
    assert "swarms" in data
    assert swarm.id in data["swarms"]
