from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer

from swan.cli.output import console, print_results
from swan.cli.commands.swarm import _resolve_swarm
from swan.cli.commands.task import _resolve_task

app = typer.Typer(help="Run swarms or individual tasks.")


@app.command("swarm")
def run_swarm(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    concurrency: Annotated[int, typer.Option("--concurrency", "-c", help="Max parallel tasks")] = 0,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show execution plan without running")] = False,
    fail_fast: Annotated[bool, typer.Option("--fail-fast", help="Abort remaining tasks on first failure")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Run all pending tasks in a swarm."""
    store = ctx.obj["store"]
    settings = ctx.obj["settings"]
    effective_concurrency = concurrency or settings.default_concurrency

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)

        from swan.core.scheduler import SwarmRunner
        runner = SwarmRunner(
            store=store,
            concurrency=effective_concurrency,
            fail_fast=fail_fast,
        )
        results = await runner.run(swarm.id, dry_run=dry_run)
        if not dry_run:
            print_results(results, as_json=as_json)

    asyncio.run(_run())


@app.command("task")
def run_task(
    ctx: typer.Context,
    task_ref: Annotated[str, typer.Argument(help="Task ID or prefix")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show plan without running")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Run a single task."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        task = _resolve_task(state, task_ref)
        agent = state.agents.get(task.agent_id)
        if agent is None:
            console.print(f"[red]Agent {task.agent_id!r} not found.[/red]")
            raise typer.Exit(1)

        if dry_run:
            console.print(f"[bold]Dry run:[/bold] task [bold]{task.name}[/bold] → agent [bold]{agent.name}[/bold] ({agent.plugin_type})")
            return

        from swan.plugins import load_plugins
        from swan.plugins.registry import PluginRegistry
        from swan.core.executor import TaskExecutor
        load_plugins()

        plugin_cls = PluginRegistry.resolve(agent.plugin_type)
        plugin = plugin_cls(agent.config)
        await plugin.setup()
        try:
            executor = TaskExecutor()
            result = await executor.run_task(task, plugin)
        finally:
            await plugin.teardown()

        await store.save_result(result)
        print_results([result], as_json=as_json)

    asyncio.run(_run())
