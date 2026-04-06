from __future__ import annotations

from typing import Annotated

import typer

from swan.cli.output import console

app = typer.Typer(help="Manage and inspect plugins.")


@app.command("list")
def plugin_list(ctx: typer.Context) -> None:
    """List all registered plugin types."""
    from swan.plugins import load_plugins
    from swan.plugins.registry import PluginRegistry
    load_plugins()
    types = PluginRegistry.list_types()
    if not types:
        console.print("[dim]No plugins registered.[/dim]")
        return
    from rich.table import Table
    from rich import box
    table = Table(box=box.SIMPLE_HEAVY, pad_edge=False)
    table.add_column("Type", style="cyan bold")
    table.add_column("Class")
    table.add_column("Module")
    for t in types:
        cls = PluginRegistry.resolve(t)
        table.add_row(t, cls.__name__, cls.__module__)
    console.print(table)


@app.command("info")
def plugin_info(
    ctx: typer.Context,
    plugin_type: Annotated[str, typer.Argument(help="Plugin type name")],
) -> None:
    """Show details about a specific plugin."""
    from swan.plugins import load_plugins
    from swan.plugins.registry import PluginRegistry, UnknownPluginError
    load_plugins()
    try:
        cls = PluginRegistry.resolve(plugin_type)
    except UnknownPluginError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    import inspect
    doc = inspect.getdoc(cls) or "(no docstring)"
    from rich.panel import Panel
    console.print(Panel(
        f"[bold]{plugin_type}[/bold]\n"
        f"[dim]Class:[/dim] {cls.__name__}\n"
        f"[dim]Module:[/dim] {cls.__module__}\n\n"
        f"{doc}",
        title="Plugin Info",
        border_style="blue",
    ))
