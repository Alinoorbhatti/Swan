from __future__ import annotations

import asyncio
import json
from typing import Annotated, Optional

import typer

from swan.core.models import Swarm
from swan.cli.output import console, print_swarm, print_swarms

app = typer.Typer(help="Manage swarms.")


@app.command("create")
def swarm_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Swarm name")],
    description: Annotated[str, typer.Option("--description", "-d", help="Optional description")] = "",
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Create a new swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        # Check for duplicate name
        for s in state.swarms.values():
            if s.name == name:
                console.print(f"[red]Error:[/red] A swarm named {name!r} already exists (id: {s.id}).")
                raise typer.Exit(1)
        swarm = Swarm.create(name=name, description=description)
        state.swarms[swarm.id] = swarm
        await store.save(state)
        if as_json:
            import json as _json
            print(_json.dumps(swarm.to_dict(), indent=2))
        else:
            console.print(f"[green]Created swarm[/green] [bold]{name}[/bold] (id: {swarm.id})")

    asyncio.run(_run())


@app.command("list")
def swarm_list(
    ctx: typer.Context,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """List all swarms."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarms = sorted(state.swarms.values(), key=lambda s: s.created_at)
        print_swarms(swarms, as_json=as_json)

    asyncio.run(_run())


@app.command("show")
def swarm_show(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Show details of a swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)
        agents = [state.agents[aid] for aid in swarm.agent_ids if aid in state.agents]
        tasks  = [state.tasks[tid]  for tid in swarm.task_ids  if tid in state.tasks]
        print_swarm(swarm, agents, tasks, as_json=as_json)

    asyncio.run(_run())


@app.command("delete")
def swarm_delete(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a swarm and all its agents and tasks."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)

        if not force:
            typer.confirm(
                f"Delete swarm {swarm.name!r} and all its agents/tasks?", abort=True
            )

        # Remove agents
        for aid in swarm.agent_ids:
            state.agents.pop(aid, None)
        # Remove tasks + results
        for tid in swarm.task_ids:
            state.tasks.pop(tid, None)
            state.results.pop(tid, None)
        del state.swarms[swarm.id]
        await store.save(state)
        console.print(f"[red]Deleted[/red] swarm [bold]{swarm.name}[/bold]")

    asyncio.run(_run())


@app.command("export")
def swarm_export(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    out: Annotated[Optional[str], typer.Option("--out", "-o", help="Output file (stdout if omitted)")] = None,
) -> None:
    """Export a swarm definition as JSON."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)
        agents = [state.agents[aid].to_dict() for aid in swarm.agent_ids if aid in state.agents]
        tasks  = [state.tasks[tid].to_dict()  for tid in swarm.task_ids  if tid in state.tasks]
        data = {"swarm": swarm.to_dict(), "agents": agents, "tasks": tasks}
        payload = json.dumps(data, indent=2)
        if out:
            with open(out, "w") as fh:
                fh.write(payload)
            console.print(f"Exported to {out}")
        else:
            print(payload)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _resolve_swarm(state, ref: str):
    """Resolve a swarm by full ID, prefix, or name."""
    # Exact ID
    if ref in state.swarms:
        return state.swarms[ref]
    # Prefix match
    matches = [s for sid, s in state.swarms.items() if sid.startswith(ref)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        console.print(f"[red]Ambiguous prefix {ref!r} matches multiple swarms.[/red]")
        raise typer.Exit(1)
    # Name match
    by_name = [s for s in state.swarms.values() if s.name == ref]
    if len(by_name) == 1:
        return by_name[0]
    if len(by_name) > 1:
        console.print(f"[red]Multiple swarms named {ref!r}. Use an ID.[/red]")
        raise typer.Exit(1)
    console.print(f"[red]Swarm {ref!r} not found.[/red]")
    raise typer.Exit(1)
