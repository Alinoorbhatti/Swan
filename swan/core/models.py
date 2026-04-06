from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from swan.core.enums import TaskStatus, ResultStatus


def _now() -> datetime:
    return datetime.utcnow()


def _new_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Swarm
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Swarm:
    id: str
    name: str
    description: str = ""
    agent_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, name: str, description: str = "") -> "Swarm":
        return cls(id=_new_id(), name=name, description=description)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Swarm":
        d = dict(d)
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        return cls(**d)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Agent:
    id: str
    swarm_id: str
    name: str
    plugin_type: str
    config: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        swarm_id: str,
        name: str,
        plugin_type: str,
        config: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> "Agent":
        return cls(
            id=_new_id(),
            swarm_id=swarm_id,
            name=name,
            plugin_type=plugin_type,
            config=config or {},
            tags=tags or [],
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Agent":
        d = dict(d)
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        return cls(**d)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Task:
    id: str
    swarm_id: str
    agent_id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)
    timeout: float | None = 30.0
    retries: int = 0
    retry_delay: float = 1.0
    depends_on: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    status: TaskStatus = TaskStatus.PENDING

    @classmethod
    def create(
        cls,
        swarm_id: str,
        agent_id: str,
        name: str,
        input: dict[str, Any] | None = None,
        timeout: float | None = 30.0,
        retries: int = 0,
        retry_delay: float = 1.0,
        depends_on: list[str] | None = None,
    ) -> "Task":
        return cls(
            id=_new_id(),
            swarm_id=swarm_id,
            agent_id=agent_id,
            name=name,
            input=input or {},
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            depends_on=depends_on or [],
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        d = dict(d)
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        d["status"] = TaskStatus(d["status"])
        return cls(**d)


# ---------------------------------------------------------------------------
# TaskResult
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class TaskResult:
    task_id: str
    agent_id: str
    swarm_id: str
    status: ResultStatus
    output: Any
    error: str | None
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    attempt: int

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "swarm_id": self.swarm_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_ms": self.duration_ms,
            "attempt": self.attempt,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskResult":
        d = dict(d)
        d["status"] = ResultStatus(d["status"])
        d["started_at"] = datetime.fromisoformat(d["started_at"])
        d["finished_at"] = datetime.fromisoformat(d["finished_at"])
        return cls(**d)
