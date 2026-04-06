from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from swan.core.models import Task


class AgentPlugin(ABC):
    """Base class for all Swan agent plugins.

    Subclasses must declare ``plugin_type`` as a class-level string
    and implement ``run()``.

    Lifecycle per swarm run:
        setup()  — called once before first task
        run()    — called once per task (possibly concurrently across instances)
        teardown() — called once after all tasks complete or on error
    """

    plugin_type: ClassVar[str]

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @abstractmethod
    async def run(self, task: Task) -> Any:
        """Execute the task. Return any JSON-serializable value or raise."""
        ...

    async def setup(self) -> None:
        """Optional: called once before the first task in a run."""

    async def teardown(self) -> None:
        """Optional: called after all tasks complete or on error."""
