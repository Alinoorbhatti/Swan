from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from swan.core.models import Agent, Swarm, Task, TaskResult


@dataclass
class StateRoot:
    version: int = 1
    swarms:  dict[str, Swarm]      = field(default_factory=dict)
    agents:  dict[str, Agent]      = field(default_factory=dict)
    tasks:   dict[str, Task]       = field(default_factory=dict)
    results: dict[str, list[TaskResult]] = field(default_factory=dict)


class StateStore(ABC):
    @abstractmethod
    async def load(self) -> StateRoot: ...

    @abstractmethod
    async def save(self, state: StateRoot) -> None: ...

    @abstractmethod
    async def save_result(self, result: TaskResult) -> None: ...

    # -- convenience helpers (default implementations use load/save) ----------

    async def get_swarm(self, swarm_id: str) -> Swarm | None:
        state = await self.load()
        return state.swarms.get(swarm_id)

    async def get_agent(self, agent_id: str) -> Agent | None:
        state = await self.load()
        return state.agents.get(agent_id)

    async def get_task(self, task_id: str) -> Task | None:
        state = await self.load()
        return state.tasks.get(task_id)

    async def get_results(self, task_id: str) -> list[TaskResult]:
        state = await self.load()
        return state.results.get(task_id, [])
