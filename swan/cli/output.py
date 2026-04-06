from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from swan.core.enums import ResultStatus
from swan.core.models import Agent, Swarm, Task, TaskResult

console = Console()
err_console = Console(stderr=True)


def is_tty() -> bool:
    return sys.stdout.isatty()


def print_json(data: Any) -> None:
    print(json.dumps(data, default=str, indent=2))


def _status_style(status: str) -> str:
    return {
        "success": "green",
        "failure": "red",
        "timeout": "yellow",
        "skipped": "dim",
        "pending": "dim",
        "running": "cyan",
        "done": "green",
        "failed": "red",
    }.get(status, "white")


# ---------------------------------------------------------------------------
# Swarms
# ---------------------------------------------------------------------------

def print_swarms(swarms: list[Swarm], as_json: bool = False) -> None:
    if as_json:
        print_json([s.to_dict() for s in swarms])
        return
    if not swarms:
        console.print("[dim]No swarms found.[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, pad_edge=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Agents", justify="right")
    table.add_column("Tasks", justify="right")
    table.add_column("Created")
    for s in swarms:
        table.add_row(
            s.id[:12] + "…",
            s.name,
            str(len(s.agent_ids)),
            str(len(s.task_ids)),
            _fmt_dt(s.created_at),
        )
    console.print(table)


def print_swarm(swarm: Swarm, agents: list[Agent], tasks: list[Task], as_json: bool = False) -> None:
    if as_json:
        print_json(swarm.to_dict())
        return
    console.print(Panel(
        f"[bold]{swarm.name}[/bold]\n"
        f"[dim]ID:[/dim] {swarm.id}\n"
        f"[dim]Description:[/dim] {swarm.description or '—'}\n"
        f"[dim]Agents:[/dim] {len(agents)}   [dim]Tasks:[/dim] {len(tasks)}\n"
        f"[dim]Created:[/dim] {_fmt_dt(swarm.created_at)}",
        title="Swarm",
        border_style="blue",
    ))


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def print_agents(agents: list[Agent], as_json: bool = False) -> None:
    if as_json:
        print_json([a.to_dict() for a in agents])
        return
    if not agents:
        console.print("[dim]No agents found.[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, pad_edge=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Tags")
    table.add_column("Created")
    for a in agents:
        table.add_row(
            a.id[:12] + "…",
            a.name,
            a.plugin_type,
            ", ".join(a.tags) or "—",
            _fmt_dt(a.created_at),
        )
    console.print(table)


def print_agent(agent: Agent, as_json: bool = False) -> None:
    if as_json:
        print_json(agent.to_dict())
        return
    cfg_lines = "\n".join(f"  {k}: {v}" for k, v in agent.config.items()) or "  (none)"
    console.print(Panel(
        f"[bold]{agent.name}[/bold]\n"
        f"[dim]ID:[/dim] {agent.id}\n"
        f"[dim]Plugin:[/dim] {agent.plugin_type}\n"
        f"[dim]Tags:[/dim] {', '.join(agent.tags) or '—'}\n"
        f"[dim]Config:[/dim]\n{cfg_lines}\n"
        f"[dim]Created:[/dim] {_fmt_dt(agent.created_at)}",
        title="Agent",
        border_style="blue",
    ))


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def print_tasks(tasks: list[Task], as_json: bool = False) -> None:
    if as_json:
        print_json([t.to_dict() for t in tasks])
        return
    if not tasks:
        console.print("[dim]No tasks found.[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, pad_edge=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Agent ID", style="dim")
    table.add_column("Depends on")
    table.add_column("Created")
    for t in tasks:
        style = _status_style(t.status.value)
        table.add_row(
            t.id[:12] + "…",
            t.name,
            f"[{style}]{t.status.value}[/{style}]",
            t.agent_id[:12] + "…",
            ", ".join(d[:8] for d in t.depends_on) or "—",
            _fmt_dt(t.created_at),
        )
    console.print(table)


def print_task(task: Task, as_json: bool = False) -> None:
    if as_json:
        print_json(task.to_dict())
        return
    style = _status_style(task.status.value)
    console.print(Panel(
        f"[bold]{task.name}[/bold]\n"
        f"[dim]ID:[/dim] {task.id}\n"
        f"[dim]Status:[/dim] [{style}]{task.status.value}[/{style}]\n"
        f"[dim]Agent:[/dim] {task.agent_id}\n"
        f"[dim]Input:[/dim] {json.dumps(task.input)}\n"
        f"[dim]Timeout:[/dim] {task.timeout}s   [dim]Retries:[/dim] {task.retries}\n"
        f"[dim]Depends on:[/dim] {', '.join(task.depends_on) or '—'}\n"
        f"[dim]Created:[/dim] {_fmt_dt(task.created_at)}",
        title="Task",
        border_style="blue",
    ))


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

def print_results(results: list[TaskResult], as_json: bool = False) -> None:
    if as_json:
        print_json([r.to_dict() for r in results])
        return
    if not results:
        console.print("[dim]No results found.[/dim]")
        return
    table = Table(box=box.SIMPLE_HEAVY, pad_edge=False)
    table.add_column("Task ID", style="cyan", no_wrap=True)
    table.add_column("Agent ID", style="dim", no_wrap=True)
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Attempt", justify="right")
    table.add_column("Finished")
    for r in results:
        style = _status_style(r.status.value)
        table.add_row(
            r.task_id[:12] + "…",
            r.agent_id[:12] + "…",
            f"[{style}]{r.status.value}[/{style}]",
            f"{r.duration_ms}ms",
            str(r.attempt),
            _fmt_dt(r.finished_at),
        )
    console.print(table)


def print_result(result: TaskResult, as_json: bool = False) -> None:
    if as_json:
        print_json(result.to_dict())
        return
    style = _status_style(result.status.value)
    output_str = json.dumps(result.output, indent=2, default=str) if result.output is not None else "—"
    console.print(Panel(
        f"[dim]Task:[/dim]  {result.task_id}\n"
        f"[dim]Agent:[/dim] {result.agent_id}\n"
        f"[dim]Status:[/dim] [{style}]{result.status.value}[/{style}]\n"
        f"[dim]Duration:[/dim] {result.duration_ms}ms   [dim]Attempt:[/dim] {result.attempt}\n"
        f"[dim]Finished:[/dim] {_fmt_dt(result.finished_at)}\n"
        f"\n[dim]Output:[/dim]\n{output_str}"
        + (f"\n\n[red]Error:[/red] {result.error}" if result.error else ""),
        title="Result",
        border_style="blue",
    ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"
