from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from swan import __version__

app = typer.Typer(
    name="swan",
    help="Orchestrate swarms of AI agents and CLI tools.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Register sub-apps
from swan.cli.commands import swarm, agent, task, run, result, plugin

app.add_typer(swarm.app,  name="swarm",  help="Manage swarms.")
app.add_typer(agent.app,  name="agent",  help="Manage agents.")
app.add_typer(task.app,   name="task",   help="Manage tasks.")
app.add_typer(run.app,    name="run",    help="Run swarms or tasks.")
app.add_typer(result.app, name="result", help="View results.")
app.add_typer(plugin.app, name="plugin", help="Inspect plugins.")


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", "-V", help="Print version and exit", is_eager=True)] = False,
    log_level: Annotated[str, typer.Option("--log-level", help="Log level (DEBUG/INFO/WARNING/ERROR)")] = "",
    config_path: Annotated[Optional[Path], typer.Option("--config", help="Path to config.toml")] = None,
    store_dir: Annotated[Optional[Path], typer.Option("--store-dir", help="Override state directory")] = None,
) -> None:
    if version:
        typer.echo(f"swan {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        return

    from swan.config import Settings
    settings = Settings.load(config_path)
    settings.ensure_dirs()

    effective_log_level = log_level.upper() if log_level else settings.log_level

    from swan.log import configure_logging
    configure_logging(
        level=effective_log_level,
        log_file=settings.log_file,
    )

    # Build state store
    if store_dir:
        from dataclasses import replace
        settings = replace(settings, state_path=store_dir / "state.json")

    from swan.state.local import JSONStateStore
    store = JSONStateStore(settings.state_path)

    ctx.ensure_object(dict)
    ctx.obj["store"] = store
    ctx.obj["settings"] = settings
