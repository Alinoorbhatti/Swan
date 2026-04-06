from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from swan.core.enums import ResultStatus
from swan.core.models import Task, TaskResult
from swan.plugins.base import AgentPlugin

log = logging.getLogger("swan.executor")


class TaskExecutor:
    """Executes a single task against an agent plugin.

    Handles timeout, exponential-backoff retry, and exception isolation.
    Never raises — always returns a TaskResult.
    """

    async def run_task(self, task: Task, plugin: AgentPlugin) -> TaskResult:
        for attempt in range(task.retries + 1):
            started_at = datetime.utcnow()
            log.debug(
                "task_started",
                extra={"task_id": task.id, "agent_id": task.agent_id, "attempt": attempt},
            )
            try:
                coro = plugin.run(task)
                if task.timeout is not None:
                    output = await asyncio.wait_for(coro, timeout=task.timeout)
                else:
                    output = await coro

                finished_at = datetime.utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                log.info(
                    "task_finished",
                    extra={
                        "task_id": task.id,
                        "agent_id": task.agent_id,
                        "status": "success",
                        "duration_ms": duration_ms,
                    },
                )
                return TaskResult(
                    task_id=task.id,
                    agent_id=task.agent_id,
                    swarm_id=task.swarm_id,
                    status=ResultStatus.SUCCESS,
                    output=output,
                    error=None,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    attempt=attempt,
                )

            except asyncio.TimeoutError:
                finished_at = datetime.utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                if attempt == task.retries:
                    log.warning(
                        "task_failed",
                        extra={"task_id": task.id, "status": "timeout", "duration_ms": duration_ms},
                    )
                    return TaskResult(
                        task_id=task.id,
                        agent_id=task.agent_id,
                        swarm_id=task.swarm_id,
                        status=ResultStatus.TIMEOUT,
                        output=None,
                        error=f"Timed out after {task.timeout}s",
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=duration_ms,
                        attempt=attempt,
                    )
                log.debug(
                    "task_retrying",
                    extra={"task_id": task.id, "attempt": attempt, "reason": "timeout"},
                )
                await asyncio.sleep(task.retry_delay * (2 ** attempt))

            except Exception as exc:
                finished_at = datetime.utcnow()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                if attempt == task.retries:
                    log.warning(
                        "task_failed",
                        extra={
                            "task_id": task.id,
                            "status": "failure",
                            "error": str(exc),
                            "duration_ms": duration_ms,
                        },
                    )
                    return TaskResult(
                        task_id=task.id,
                        agent_id=task.agent_id,
                        swarm_id=task.swarm_id,
                        status=ResultStatus.FAILURE,
                        output=None,
                        error=str(exc),
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=duration_ms,
                        attempt=attempt,
                    )
                log.debug(
                    "task_retrying",
                    extra={"task_id": task.id, "attempt": attempt, "reason": str(exc)},
                )
                await asyncio.sleep(task.retry_delay * (2 ** attempt))

        # Unreachable, but satisfies type checkers
        raise RuntimeError("TaskExecutor loop exited without returning")  # pragma: no cover
