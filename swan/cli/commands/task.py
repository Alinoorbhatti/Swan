from __future__ import annotations

import asyncio
import json
from typing import Annotated, Optional

import typer

from swan.core.enums import TaskStatus
from swan.core.models import Task
from swan.cli.output import console, print_task, print_tasks
from swan.cli.commands.swarm import _resolve_swarm
from swan.cli.commands.agent import _resolve_agent

app = typer.Typer(help="Manage tasks within a swarm.")


def _parse_input(pairs: list[str]) -> dict:
    result = {}
    for pair in pairs:
        if "=" not in pair:
            console.print(f"[red]Invalid input pair {pair!r}. Expected KEY=VALUE.[/red]")
            raise typer.Exit(1)
        k, _, v = pair.partition("=")
        try:
            result[k.strip()] = json.loads(v)
        except (json.JSONDecodeError, ValueError):
            result[k.strip()] = v
    return result


@app.command("add")
def task_add(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    name: Annotated[str, typer.Option("--name", "-n", help="Task name")] = "",
    agent_ref: Annotated[str, typer.Option("--agent", "-a", help="Agent ID or name")] = "",
    input_pairs: Annotated[Optional[list[str]], typer.Option("--input", "-i", help="KEY=VALUE input pairs")] = None,
    timeout: Annotated[Optional[float], typer.Option("--timeout", help="Timeout seconds")] = 30.0,
    retries: Annotated[int, typer.Option("--retries", help="Retry count")] = 0,
    depends_on: Annotated[Optional[list[str]], typer.Option("--depends-on", help="Dependency task IDs")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Add a task to a swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)
        agent = _resolve_agent(state, agent_ref)

        if agent.swarm_id != swarm.id:
            console.print(f"[red]Agent {agent.name!r} does not belong to swarm {swarm.name!r}.[/red]")
            raise typer.Exit(1)

        inp = _parse_input(input_pairs or [])
        task_name = name or f"task-{len(swarm.task_ids) + 1}"
        task = Task.create(
            swarm_id=swarm.id,
            agent_id=agent.id,
            name=task_name,
            input=inp,
            timeout=timeout,
            retries=retries,
            depends_on=depends_on or [],
        )
        state.tasks[task.id] = task
        swarm.task_ids.append(task.id)
        await store.save(state)

        if as_json:
            print(json.dumps(task.to_dict(), indent=2))
        else:
            console.print(
                f"[green]Added task[/green] [bold]{task_name}[/bold] "
                f"(id: {task.id}) → agent [bold]{agent.name}[/bold]"
            )

    asyncio.run(_run())


@app.command("list")
def task_list(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter by status")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """List tasks in a swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)
        tasks = [state.tasks[tid] for tid in swarm.task_ids if tid in state.tasks]
        if status:
            try:
                filter_status = TaskStatus(status)
            except ValueError:
                console.print(f"[red]Unknown status {status!r}. Valid: {[s.value for s in TaskStatus]}[/red]")
                raise typer.Exit(1)
            tasks = [t for t in tasks if t.status == filter_status]
        print_tasks(tasks, as_json=as_json)

    asyncio.run(_run())


@app.command("show")
def task_show(
    ctx: typer.Context,
    task_ref: Annotated[str, typer.Argument(help="Task ID or prefix")],
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Show task details."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        task = _resolve_task(state, task_ref)
        print_task(task, as_json=as_json)

    asyncio.run(_run())


@app.command("remove")
def task_remove(
    ctx: typer.Context,
    task_ref: Annotated[str, typer.Argument(help="Task ID or prefix")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Remove a task from its swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        task = _resolve_task(state, task_ref)

        if not force:
            typer.confirm(f"Remove task {task.name!r}?", abort=True)

        swarm = state.swarms.get(task.swarm_id)
        if swarm and task.id in swarm.task_ids:
            swarm.task_ids.remove(task.id)
        del state.tasks[task.id]
        state.results.pop(task.id, None)
        await store.save(state)
        console.print(f"[red]Removed[/red] task [bold]{task.name}[/bold]")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_task(state, ref: str):
    if ref in state.tasks:
        return state.tasks[ref]
    matches = [t for tid, t in state.tasks.items() if tid.startswith(ref)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        console.print(f"[red]Ambiguous prefix {ref!r}.[/red]")
        raise typer.Exit(1)
    by_name = [t for t in state.tasks.values() if t.name == ref]
    if len(by_name) == 1:
        return by_name[0]
    console.print(f"[red]Task {ref!r} not found.[/red]")
    raise typer.Exit(1)
