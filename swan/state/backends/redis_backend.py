"""
Redis state backend — stub implementation.

TODO: Implement using aioredis once the Redis optional dep is added.
Install: pip install swan[redis]

This backend enables:
- Distributed swarm state shared across multiple processes/machines
- A future `swan worker` daemon that pulls tasks from a Redis queue
- Atomic state updates via Redis transactions
"""
from swan.state.base import StateRoot, StateStore
from swan.core.models import TaskResult


class RedisStateStore(StateStore):
    def __init__(self, url: str, key_prefix: str = "swan:") -> None:
        self._url = url
        self._prefix = key_prefix
        raise NotImplementedError(
            "Redis backend is not yet implemented. "
            "Install aioredis and implement RedisStateStore. "
            "See swan/state/backends/redis_backend.py for the interface."
        )

    async def load(self) -> StateRoot:
        raise NotImplementedError

    async def save(self, state: StateRoot) -> None:
        raise NotImplementedError

    async def save_result(self, result: TaskResult) -> None:
        raise NotImplementedError
