from datetime import datetime
from swan.core.enums import TaskStatus, ResultStatus
from swan.core.models import Agent, Swarm, Task, TaskResult


def test_swarm_roundtrip():
    s = Swarm.create("my-swarm", "A test swarm")
    d = s.to_dict()
    s2 = Swarm.from_dict(d)
    assert s2.id == s.id
    assert s2.name == s.name
    assert s2.description == s.description
    assert isinstance(s2.created_at, datetime)


def test_agent_roundtrip():
    a = Agent.create("swarm-1", "worker", "shell", config={"command": "echo hi"})
    d = a.to_dict()
    a2 = Agent.from_dict(d)
    assert a2.id == a.id
    assert a2.plugin_type == "shell"
    assert a2.config == {"command": "echo hi"}


def test_task_roundtrip():
    t = Task.create("swarm-1", "agent-1", "my-task", input={"prompt": "hello"}, timeout=60.0, retries=2)
    d = t.to_dict()
    t2 = Task.from_dict(d)
    assert t2.id == t.id
    assert t2.status == TaskStatus.PENDING
    assert t2.timeout == 60.0
    assert t2.retries == 2


def test_task_result_roundtrip():
    now = datetime.utcnow()
    r = TaskResult(
        task_id="t1", agent_id="a1", swarm_id="s1",
        status=ResultStatus.SUCCESS, output={"stdout": "hello"},
        error=None, started_at=now, finished_at=now, duration_ms=42, attempt=0,
    )
    d = r.to_dict()
    r2 = TaskResult.from_dict(d)
    assert r2.status == ResultStatus.SUCCESS
    assert r2.duration_ms == 42
    assert r2.output == {"stdout": "hello"}
