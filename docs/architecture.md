# Architecture

This document explains Swan's internal design: layer responsibilities, key interfaces, and the reasoning behind architectural decisions.

---

## Layer overview

```
┌─────────────────────────────────────────────────────┐
│  CLI  (swan/cli/)                                   │
│  Typer commands — parse args, call core, render UI  │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│  Core  (swan/core/)                                 │
│  Scheduler → Executor → Plugin                      │
└────────┬────────────────────┬────────────────────────┘
         │                    │
┌────────▼────────┐  ┌────────▼────────────────────────┐
│  State          │  │  Plugins  (swan/plugins/)        │
│  (swan/state/)  │  │  AgentPlugin ABC + Registry      │
│  StateStore ABC │  │  builtin: shell, http, claude    │
│  JSONStateStore │  │  third-party via entry-points    │
└─────────────────┘  └──────────────────────────────────┘
```

Each layer has one job. The CLI layer contains zero business logic. Core contains zero I/O. Plugins know nothing about state.

---

## Module responsibilities

### `swan/cli/`

- **`main.py`** — root Typer app; reads settings, builds the store, passes both into subcommands via `ctx.obj`
- **`output.py`** — all Rich formatting: tables, panels, JSON printing, status colour-coding
- **`commands/`** — one file per noun (`swarm`, `agent`, `task`, `run`, `result`, `plugin`); each command is a thin adapter between CLI args and core objects

The CLI never touches asyncio directly except in `run.py`, which calls `asyncio.run(scheduler.run(...))`.

### `swan/core/`

- **`models.py`** — `Swarm`, `Agent`, `Task`, `TaskResult` dataclasses with `to_dict()` / `from_dict()` for JSON serialisation
- **`enums.py`** — `TaskStatus`, `ResultStatus`
- **`executor.py`** — `TaskExecutor.run_task()`: wraps a single plugin call with `asyncio.wait_for` and exponential-backoff retry; always returns a `TaskResult`, never raises
- **`scheduler.py`** — `topological_waves()` (pure function, dependency sort) + `SwarmRunner` (orchestrates waves, manages plugin lifecycle)

### `swan/plugins/`

- **`base.py`** — `AgentPlugin` ABC with `run()` (required), `setup()` / `teardown()` (optional)
- **`registry.py`** — `PluginRegistry` singleton: a class-level dict from `plugin_type → class`
- **`__init__.py`** — `load_plugins()`: registers builtins first, then discovers third-party plugins via `importlib.metadata.entry_points(group="swan.plugins")`
- **`builtin/`** — `shell.py`, `http.py`, `claude.py`

### `swan/state/`

- **`base.py`** — `StateStore` ABC and `StateRoot` dataclass (holds all in-memory state)
- **`local.py`** — `JSONStateStore`: reads/writes `~/.swan/state.json`; uses `asyncio.run_in_executor` for sync I/O; atomic writes via `os.replace`
- **`backends/redis_backend.py`** — stub with `NotImplementedError`; documents the interface contract for future implementation

### Root-level modules

- **`config.py`** — `Settings` frozen dataclass; reads `~/.swan/config.toml` with stdlib `tomllib`, merges env vars
- **`log.py`** — `configure_logging()`: attaches `RichHandler` (console) and `RotatingFileHandler` with `JsonFormatter` (file)

---

## Key design decisions

### Why `asyncio.TaskGroup` instead of `asyncio.gather`?

`asyncio.gather` swallows individual task exceptions by default (you need `return_exceptions=True`) and if one task cancels the group, others may be left dangling.

`asyncio.TaskGroup` (Python 3.11+) provides **structured concurrency**: if any task raises an unhandled exception, the entire group is cancelled cleanly and the exception propagates. This makes failure modes predictable.

Swan's executor catches all exceptions internally and returns a `TaskResult(status=failure)`, so `TaskGroup` never sees an exception from normal task failures — only from genuine programming errors.

### Why per-wave dispatch instead of one giant gather?

Waves encode the dependency order. Running all tasks simultaneously would violate `depends_on` constraints. Waves are the minimal scheduling unit that respects dependencies while maximising concurrency within each batch.

### Why atomic writes for the state file?

A crash mid-write could leave a partially-written JSON file that can't be parsed. The write-then-rename pattern (`os.replace`) is atomic on POSIX: the rename either completes or doesn't happen at all. The existing state file is always intact.

### Why entry-points for plugins instead of a config-declared list?

Entry-points decouple plugin installation from Swan's configuration. A user installs `pip install my-plugin` and Swan discovers it automatically on the next run — no config file edits required. This is the same pattern used by pytest plugins, Flask extensions, and many other ecosystems.

### Why `dataclasses` instead of Pydantic?

Swan's models are simple, immutable value objects with explicit serialisation. stdlib `dataclasses` + manual `to_dict/from_dict` keeps the dependency count low and the serialisation logic transparent. Pydantic is recommended for plugin config validation but is optional (plugins may use it if they wish).

---

## Data flow: `swan run swarm myswarm`

```
CLI (run.py)
  asyncio.run(
    SwarmRunner.run("myswarm")
  )
    │
    ├── StateStore.load()
    │     JSONStateStore reads ~/.swan/state.json
    │     Returns StateRoot {swarms, agents, tasks, results}
    │
    ├── load_plugins()
    │     PluginRegistry.register(ShellPlugin)
    │     PluginRegistry.register(HttpPlugin)
    │     # ... entry-point discovery ...
    │
    ├── Instantiate plugins: {agent_id: PluginClass(agent.config)}
    ├── await plugin.setup() for each
    │
    ├── topological_waves(tasks)
    │     Kahn's algorithm → [[T1, T2], [T3], [T4]]
    │
    ├── for wave in waves:
    │     async with asyncio.TaskGroup() as tg:
    │         for task in wave:
    │             tg.create_task(
    │                 _run_with_sem(task, plugin, semaphore)
    │             )
    │         # TaskGroup awaits all, cancels on unhandled exception
    │
    │     for result in wave_results:
    │         await StateStore.save_result(result)
    │
    ├── await plugin.teardown() for each
    │
    └── return all_results
          │
          CLI renders results table (output.py)
```

---

## Extension points

### Adding a new state backend

1. Create `swan/state/backends/my_backend.py`
2. Implement `StateStore` ABC: `load()`, `save()`, `save_result()`
3. Wire it in `swan/cli/main.py` where the store is constructed based on `settings.state_backend`

No other code changes are needed.

### Adding a new plugin

See [plugins.md](plugins.md). The registry and loader are fully generic.

### Supporting distributed workers (`swan worker`)

The planned architecture:
- `swan run swarm` becomes a **producer**: writes tasks to a Redis queue instead of executing them directly
- `swan worker` is a **consumer daemon**: pulls tasks from the queue, executes them, writes results back
- `RedisStateStore` handles shared state
- The `SwarmRunner` scheduler, `TaskExecutor`, and all plugins are reused unchanged

This works because `StateStore` is an interface and `TaskExecutor` is pure async — neither knows where tasks come from.
