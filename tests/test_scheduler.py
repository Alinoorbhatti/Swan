import pytest
from swan.core.scheduler import topological_waves, CyclicDependencyError
from swan.core.models import Task
from swan.core.enums import TaskStatus
from datetime import datetime


def _task(id: str, depends_on: list[str] | None = None) -> Task:
    return Task(
        id=id, swarm_id="s1", agent_id="a1", name=id,
        input={}, timeout=30.0, retries=0, retry_delay=1.0,
        depends_on=depends_on or [],
        created_at=datetime.utcnow(),
        status=TaskStatus.PENDING,
    )


def test_no_tasks():
    assert topological_waves([]) == []


def test_single_task():
    waves = topological_waves([_task("a")])
    assert len(waves) == 1
    assert waves[0][0].id == "a"


def test_independent_tasks_single_wave():
    tasks = [_task("a"), _task("b"), _task("c")]
    waves = topological_waves(tasks)
    assert len(waves) == 1
    ids = {t.id for t in waves[0]}
    assert ids == {"a", "b", "c"}


def test_linear_chain():
    # a → b → c
    tasks = [_task("a"), _task("b", ["a"]), _task("c", ["b"])]
    waves = topological_waves(tasks)
    assert len(waves) == 3
    assert waves[0][0].id == "a"
    assert waves[1][0].id == "b"
    assert waves[2][0].id == "c"


def test_diamond():
    # a → b, a → c, b → d, c → d
    tasks = [
        _task("a"),
        _task("b", ["a"]),
        _task("c", ["a"]),
        _task("d", ["b", "c"]),
    ]
    waves = topological_waves(tasks)
    assert len(waves) == 3
    assert waves[0][0].id == "a"
    assert {t.id for t in waves[1]} == {"b", "c"}
    assert waves[2][0].id == "d"


def test_cyclic_raises():
    tasks = [_task("a", ["b"]), _task("b", ["a"])]
    with pytest.raises(CyclicDependencyError):
        topological_waves(tasks)


def test_external_dep_ignored():
    # "external" is not in the task list — should be treated as satisfied
    tasks = [_task("a", ["external"]), _task("b", ["a"])]
    waves = topological_waves(tasks)
    assert len(waves) == 2
    assert waves[0][0].id == "a"
    assert waves[1][0].id == "b"
