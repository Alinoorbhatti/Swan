from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer

from swan.core.enums import ResultStatus
from swan.cli.output import console, print_result, print_results
from swan.cli.commands.swarm import _resolve_swarm
from swan.cli.commands.task import _resolve_task

app = typer.Typer(help="View task results.")


@app.command("list")
def result_list(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter by status")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """List all results for a swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)
        all_results = []
        for tid in swarm.task_ids:
            all_results.extend(state.results.get(tid, []))

        if status:
            try:
                filter_status = ResultStatus(status)
            except ValueError:
                console.print(f"[red]Unknown status {status!r}.[/red]")
                raise typer.Exit(1)
            all_results = [r for r in all_results if r.status == filter_status]

        print_results(all_results, as_json=as_json)

    asyncio.run(_run())


@app.command("show")
def result_show(
    ctx: typer.Context,
    task_ref: Annotated[str, typer.Argument(help="Task ID or prefix")],
    attempt: Annotated[int, typer.Option("--attempt", help="Attempt number (default: latest)")] = -1,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Show the result for a specific task."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        task = _resolve_task(state, task_ref)
        results = state.results.get(task.id, [])
        if not results:
            console.print(f"[dim]No results found for task {task.name!r}.[/dim]")
            return
        result = results[attempt]
        print_result(result, as_json=as_json)

    asyncio.run(_run())
