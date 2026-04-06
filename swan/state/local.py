from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from swan.core.models import Agent, Swarm, Task, TaskResult
from swan.state.base import StateRoot, StateStore

log = logging.getLogger("swan.state")


class JSONStateStore(StateStore):
    """Persists state to a single JSON file with atomic writes."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._cache: StateRoot | None = None

    # ------------------------------------------------------------------
    # Internal sync helpers (run in executor to avoid blocking event loop)
    # ------------------------------------------------------------------

    def _read_sync(self) -> StateRoot:
        if not self._path.exists():
            return StateRoot()
        with open(self._path) as fh:
            raw = json.load(fh)
        return _deserialize(raw)

    def _write_sync(self, state: StateRoot) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        with open(tmp, "w") as fh:
            json.dump(_serialize(state), fh, indent=2)
        os.replace(tmp, self._path)
        log.debug("state_saved", extra={"path": str(self._path)})

    # ------------------------------------------------------------------
    # StateStore interface
    # ------------------------------------------------------------------

    async def load(self) -> StateRoot:
        if self._cache is not None:
            return self._cache
        loop = asyncio.get_event_loop()
        self._cache = await loop.run_in_executor(None, self._read_sync)
        return self._cache

    async def save(self, state: StateRoot) -> None:
        self._cache = state
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_sync, state)

    async def save_result(self, result: TaskResult) -> None:
        state = await self.load()
        state.results.setdefault(result.task_id, []).append(result)
        await self.save(state)

    def invalidate_cache(self) -> None:
        self._cache = None


# ------------------------------------------------------------------
# Serialization helpers
# ------------------------------------------------------------------

def _serialize(state: StateRoot) -> dict:
    return {
        "version": state.version,
        "swarms":  {k: v.to_dict() for k, v in state.swarms.items()},
        "agents":  {k: v.to_dict() for k, v in state.agents.items()},
        "tasks":   {k: v.to_dict() for k, v in state.tasks.items()},
        "results": {
            k: [r.to_dict() for r in v]
            for k, v in state.results.items()
        },
    }


def _deserialize(raw: dict) -> StateRoot:
    return StateRoot(
        version=raw.get("version", 1),
        swarms={k: Swarm.from_dict(v) for k, v in raw.get("swarms", {}).items()},
        agents={k: Agent.from_dict(v) for k, v in raw.get("agents", {}).items()},
        tasks ={k: Task.from_dict(v)  for k, v in raw.get("tasks",  {}).items()},
        results={
            k: [TaskResult.from_dict(r) for r in v]
            for k, v in raw.get("results", {}).items()
        },
    )
