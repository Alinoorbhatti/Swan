from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque

from swan.core.enums import ResultStatus
from swan.core.executor import TaskExecutor
from swan.core.models import Agent, Swarm, Task, TaskResult
from swan.plugins.base import AgentPlugin
from swan.plugins.registry import PluginRegistry
from swan.state.base import StateStore

log = logging.getLogger("swan.scheduler")


class CyclicDependencyError(ValueError):
    pass


def topological_waves(tasks: list[Task]) -> list[list[Task]]:
    """Return tasks grouped into sequential waves using Kahn's algorithm.

    Tasks within a wave have no dependencies on each other and can run
    concurrently.  Each wave depends only on tasks in prior waves.
    """
    if not tasks:
        return []

    task_map = {t.id: t for t in tasks}
    in_degree: dict[str, int] = {t.id: 0 for t in tasks}
    dependents: dict[str, list[str]] = defaultdict(list)  # id → list of tasks that depend on it

    for task in tasks:
        for dep_id in task.depends_on:
            if dep_id not in task_map:
                # Dependency is outside this run — treat as already satisfied
                continue
            in_degree[task.id] += 1
            dependents[dep_id].append(task.id)

    waves: list[list[Task]] = []
    queue: deque[str] = deque(tid for tid, deg in in_degree.items() if deg == 0)

    processed = 0
    while queue:
        wave_ids = list(queue)
        queue.clear()

        wave = [task_map[tid] for tid in wave_ids]
        waves.append(wave)
        processed += len(wave)

        for tid in wave_ids:
            for dep_tid in dependents[tid]:
                in_degree[dep_tid] -= 1
                if in_degree[dep_tid] == 0:
                    queue.append(dep_tid)

    if processed < len(tasks):
        raise CyclicDependencyError(
            f"Cyclic dependency detected among tasks: "
            f"{[t.id for t in tasks if in_degree[t.id] > 0]}"
        )

    return waves


class SwarmRunner:
    """Orchestrates a full swarm run: load state → schedule → execute → persist."""

    def __init__(
        self,
        store: StateStore,
        concurrency: int = 10,
        fail_fast: bool = False,
    ) -> None:
        self._store = store
        self._concurrency = concurrency
        self._fail_fast = fail_fast
        self._executor = TaskExecutor()

    async def run(
        self,
        swarm_id: str,
        task_ids: list[str] | None = None,
        dry_run: bool = False,
    ) -> list[TaskResult]:
        """Run all (or a subset of) tasks in a swarm.

        Args:
            swarm_id:  The swarm to run.
            task_ids:  Specific task IDs to run; None means all pending tasks.
            dry_run:   Print the execution plan without actually running.
        """
        state = await self._store.load()

        swarm: Swarm | None = state.swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"Swarm {swarm_id!r} not found")

        # Collect tasks to run
        candidate_ids = task_ids if task_ids is not None else swarm.task_ids
        tasks = [state.tasks[tid] for tid in candidate_ids if tid in state.tasks]
        agents = {aid: state.agents[aid] for aid in swarm.agent_ids if aid in state.agents}

        waves = topological_waves(tasks)

        if dry_run:
            self._print_plan(swarm, waves, agents)
            return []

        log.info(
            "swarm_run_started",
            extra={"swarm_id": swarm_id, "task_count": len(tasks), "wave_count": len(waves)},
        )

        from swan.plugins import load_plugins
        load_plugins()

        # Instantiate one plugin per agent (reused across tasks)
        plugin_instances: dict[str, AgentPlugin] = {}
        for agent in agents.values():
            plugin_cls = PluginRegistry.resolve(agent.plugin_type)
            plugin_instances[agent.id] = plugin_cls(agent.config)

        # Setup
        for plugin in plugin_instances.values():
            await plugin.setup()

        all_results: list[TaskResult] = []
        sem = asyncio.Semaphore(self._concurrency)
        aborted = False

        try:
            for wave in waves:
                if aborted:
                    # Mark remaining tasks as skipped
                    for task in wave:
                        plugin = plugin_instances.get(task.agent_id)
                        if plugin is None:
                            continue
                        from datetime import datetime
                        now = datetime.utcnow()
                        result = TaskResult(
                            task_id=task.id, agent_id=task.agent_id, swarm_id=swarm_id,
                            status=ResultStatus.SKIPPED, output=None, error="aborted due to fail-fast",
                            started_at=now, finished_at=now, duration_ms=0, attempt=0,
                        )
                        all_results.append(result)
                        await self._store.save_result(result)
                    continue

                wave_results = await self._run_wave(wave, plugin_instances, sem)
                all_results.extend(wave_results)

                for r in wave_results:
                    await self._store.save_result(r)

                if self._fail_fast and any(
                    r.status in (ResultStatus.FAILURE, ResultStatus.TIMEOUT)
                    for r in wave_results
                ):
                    log.warning("fail_fast triggered — skipping remaining waves")
                    aborted = True
        finally:
            for plugin in plugin_instances.values():
                await plugin.teardown()

        log.info(
            "swarm_run_finished",
            extra={
                "swarm_id": swarm_id,
                "total": len(all_results),
                "success": sum(1 for r in all_results if r.status == ResultStatus.SUCCESS),
                "failed": sum(1 for r in all_results if r.status == ResultStatus.FAILURE),
            },
        )
        return all_results

    async def _run_wave(
        self,
        tasks: list[Task],
        plugins: dict[str, AgentPlugin],
        sem: asyncio.Semaphore,
    ) -> list[TaskResult]:
        results: list[TaskResult] = []

        async def _run_one(task: Task) -> None:
            plugin = plugins.get(task.agent_id)
            if plugin is None:
                from datetime import datetime
                now = datetime.utcnow()
                results.append(TaskResult(
                    task_id=task.id, agent_id=task.agent_id, swarm_id=task.swarm_id,
                    status=ResultStatus.FAILURE, output=None,
                    error=f"Agent {task.agent_id!r} not found in swarm",
                    started_at=now, finished_at=now, duration_ms=0, attempt=0,
                ))
                return
            async with sem:
                result = await self._executor.run_task(task, plugin)
            results.append(result)

        async with asyncio.TaskGroup() as tg:
            for task in tasks:
                tg.create_task(_run_one(task))

        return results

    def _print_plan(
        self,
        swarm: Swarm,
        waves: list[list[Task]],
        agents: dict[str, Agent],
    ) -> None:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        console.print(f"\n[bold]Dry run — swarm:[/bold] {swarm.name} ({swarm.id[:8]}…)\n")

        for i, wave in enumerate(waves, 1):
            table = Table(title=f"Wave {i} ({len(wave)} task(s))", box=None, pad_edge=False)
            table.add_column("Task ID", style="cyan")
            table.add_column("Name")
            table.add_column("Agent")
            table.add_column("Plugin")
            table.add_column("Depends on")
            for task in wave:
                agent = agents.get(task.agent_id)
                table.add_row(
                    task.id[:8] + "…",
                    task.name,
                    agent.name if agent else task.agent_id[:8],
                    agent.plugin_type if agent else "?",
                    ", ".join(d[:8] for d in task.depends_on) or "—",
                )
            console.print(table)
            console.print()
