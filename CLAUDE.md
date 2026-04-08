# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable) with dev tools
pip install -e ".[dev]"

# Install with Claude AI plugin support
pip install -e ".[claude]"

# Run all tests (~23 tests, ~0.2s)
pytest tests/ -v

# Run a single test file
pytest tests/test_scheduler.py -v

# Run a single test by name
pytest tests/test_executor.py -k "test_retry" -v
```

No linter is configured. `pytest` is the only dev tool declared in `pyproject.toml`.

## Architecture

Swan is a Python CLI (Typer + Rich) that orchestrates **swarms** of typed agent workers.

### Data flow

```
CLI command
  → StateStore.load()          # read ~/.swan/state.json
  → mutate StateRoot           # add swarm / agent / task
  → StateStore.save()          # atomic write back
  ↓
swan run swarm <name>
  → SwarmRunner.run()          # load state, build plugin instances
  → topological_waves(tasks)   # Kahn's algorithm → [[wave1], [wave2], …]
  → asyncio.TaskGroup          # concurrent tasks within each wave, semaphore-limited
  → TaskExecutor.run_task()    # timeout + exponential-backoff retry; never raises
  → StateStore.save_result()   # persist TaskResult
```

### Key modules

| Path | Role |
|------|------|
| `swan/core/models.py` | Dataclasses: `Swarm`, `Agent`, `Task`, `TaskResult` — all have `to_dict`/`from_dict` |
| `swan/core/scheduler.py` | `topological_waves()` + `SwarmRunner` (orchestration) |
| `swan/core/executor.py` | `TaskExecutor` — single-task execution with retry/timeout |
| `swan/state/base.py` | `StateStore` ABC + `StateRoot` container |
| `swan/state/local.py` | `JSONStateStore` — atomic JSON file, in-memory cache, async via executor |
| `swan/plugins/base.py` | `AgentPlugin` ABC — `plugin_type`, `run()`, optional `setup()`/`teardown()` |
| `swan/plugins/registry.py` | `PluginRegistry` — dict keyed by `plugin_type` string |
| `swan/plugins/builtin/` | `shell`, `http`, `claude` plugins |
| `swan/cli/commands/` | One file per command group (`swarm`, `agent`, `task`, `run`, `result`, `plugin`) |
| `swan/cli/output.py` | Shared Rich table/JSON output helpers |
| `swan/config.py` | Config loading from `~/.swan/config.toml` + env vars |

### Plugin system

Plugins register via Python entry points (`swan.plugins` group in `pyproject.toml`). At runtime, `swan/plugins/__init__.py:load_plugins()` calls `importlib.metadata.entry_points` and calls `PluginRegistry.register()` for each discovered class. The `claude` plugin is **not** registered via entry points — it's imported directly when `anthropic` is installed.

To write a custom plugin: subclass `AgentPlugin`, set `plugin_type = "mytype"`, implement `async run(task) -> Any`, and declare the entry point in your package's `pyproject.toml`.

### State

All state lives in a single `StateRoot` (`~/.swan/state.json` by default). Keys are hex UUIDs. `JSONStateStore` caches the parsed state in memory for the lifetime of one command; call `invalidate_cache()` if you need a fresh read within the same process. The Redis backend stub (`swan/state/backends/redis_backend.py`) is not yet implemented.

---

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
