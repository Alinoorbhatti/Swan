from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer

from swan.core.models import Agent
from swan.cli.output import console, print_agent, print_agents
from swan.cli.commands.swarm import _resolve_swarm

app = typer.Typer(help="Manage agents within a swarm.")


def _parse_config(pairs: list[str]) -> dict:
    """Parse KEY=VALUE pairs into a dict."""
    config = {}
    for pair in pairs:
        if "=" not in pair:
            console.print(f"[red]Invalid config pair {pair!r}. Expected KEY=VALUE.[/red]")
            raise typer.Exit(1)
        k, _, v = pair.partition("=")
        # Try to parse value as JSON (handles numbers, bools, nested dicts)
        import json
        try:
            config[k.strip()] = json.loads(v)
        except (json.JSONDecodeError, ValueError):
            config[k.strip()] = v
    return config


@app.command("add")
def agent_add(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    name: Annotated[str, typer.Argument(help="Agent name")],
    plugin_type: Annotated[str, typer.Option("--type", "-t", help="Plugin type (shell, http, claude, …)")],
    config: Annotated[Optional[list[str]], typer.Option("--config", "-c", help="KEY=VALUE plugin config pairs")] = None,
    tags: Annotated[Optional[list[str]], typer.Option("--tag", help="Tags")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Add an agent to a swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)

        cfg = _parse_config(config or [])
        agent = Agent.create(
            swarm_id=swarm.id,
            name=name,
            plugin_type=plugin_type,
            config=cfg,
            tags=tags or [],
        )
        state.agents[agent.id] = agent
        swarm.agent_ids.append(agent.id)
        await store.save(state)

        if as_json:
            import json
            print(json.dumps(agent.to_dict(), indent=2))
        else:
            console.print(
                f"[green]Added agent[/green] [bold]{name}[/bold] "
                f"(type: {plugin_type}, id: {agent.id}) to swarm [bold]{swarm.name}[/bold]"
            )

    asyncio.run(_run())


@app.command("list")
def agent_list(
    ctx: typer.Context,
    swarm_ref: Annotated[str, typer.Argument(help="Swarm ID or name")],
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """List agents in a swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        swarm = _resolve_swarm(state, swarm_ref)
        agents = [state.agents[aid] for aid in swarm.agent_ids if aid in state.agents]
        print_agents(agents, as_json=as_json)

    asyncio.run(_run())


@app.command("show")
def agent_show(
    ctx: typer.Context,
    agent_ref: Annotated[str, typer.Argument(help="Agent ID or prefix")],
    as_json: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Show agent details."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        agent = _resolve_agent(state, agent_ref)
        print_agent(agent, as_json=as_json)

    asyncio.run(_run())


@app.command("remove")
def agent_remove(
    ctx: typer.Context,
    agent_ref: Annotated[str, typer.Argument(help="Agent ID or prefix")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Remove an agent from its swarm."""
    store = ctx.obj["store"]

    async def _run() -> None:
        state = await store.load()
        agent = _resolve_agent(state, agent_ref)

        if not force:
            typer.confirm(f"Remove agent {agent.name!r}?", abort=True)

        swarm = state.swarms.get(agent.swarm_id)
        if swarm and agent.id in swarm.agent_ids:
            swarm.agent_ids.remove(agent.id)
        del state.agents[agent.id]
        await store.save(state)
        console.print(f"[red]Removed[/red] agent [bold]{agent.name}[/bold]")

    asyncio.run(_run())


@app.command("types")
def agent_types(ctx: typer.Context) -> None:
    """List all registered plugin types."""
    from swan.plugins import load_plugins
    from swan.plugins.registry import PluginRegistry
    load_plugins()
    types = PluginRegistry.list_types()
    if not types:
        console.print("[dim]No plugins registered.[/dim]")
        return
    for t in types:
        console.print(f"  [cyan]{t}[/cyan]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_agent(state, ref: str):
    if ref in state.agents:
        return state.agents[ref]
    matches = [a for aid, a in state.agents.items() if aid.startswith(ref)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        console.print(f"[red]Ambiguous prefix {ref!r}.[/red]")
        raise typer.Exit(1)
    # Name match
    by_name = [a for a in state.agents.values() if a.name == ref]
    if len(by_name) == 1:
        return by_name[0]
    console.print(f"[red]Agent {ref!r} not found.[/red]")
    raise typer.Exit(1)
