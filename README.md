<p align="center">
  <img src="docs/logo.svg" alt="Swan — Agent Orchestration" width="420"/>
</p>

<p align="center">
  <strong>Orchestrate swarms of AI agents and CLI tools from your terminal.</strong>
</p>

<p align="center">
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12+"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" alt="MIT License"/></a>
  <img src="https://img.shields.io/badge/tests-23%20passing-22c55e?style=flat-square" alt="Tests passing"/>
  <img src="https://img.shields.io/badge/version-0.1.0-7ec8e3?style=flat-square" alt="Version 0.1.0"/>
</p>

---

Swan is a lightweight Python CLI for running **swarms of agents** — shell commands, HTTP endpoints, Claude AI models, or any custom plugin — concurrently, with dependency ordering, retry logic, and structured logging. No config files required to get started.

---

## Table of Contents

- [Why Swan?](#why-swan)
- [Install](#install)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [CLI Reference](#cli-reference)
- [Built-in Plugins](#built-in-plugins)
- [Task Dependencies](#task-dependencies)
- [Writing a Custom Plugin](#writing-a-custom-plugin)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Development](#development)
- [Roadmap](#roadmap)
- [License](#license)

---

## Why Swan?

| Problem | Swan's answer |
|---|---|
| Running multiple AI/CLI tasks manually | One command: `swan run swarm myswarm` |
| Coordinating tasks that depend on each other | Declare `--depends-on`; Swan schedules automatically |
| Adding new agent types without forking | Python entry-point plugin system |
| Scripting and automation | Every command supports `--json` output |
| Scaling to distributed workers later | State store is swappable (JSON → Redis) |

---

## Install

**Requires Python 3.12+**

```bash
git clone https://github.com/Alinoorbhatti/Swan.git
cd Swan
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

**Optional extras:**

```bash
pip install -e ".[claude]"   # Claude AI agent plugin  (needs ANTHROPIC_API_KEY)
pip install -e ".[dev]"      # pytest + pytest-asyncio for development
pip install -e ".[redis]"    # Redis state backend     (coming soon)
```

---

## Quick Start

```bash
# 1. Create a swarm
swan swarm create demo --description "My first swarm"

# 2. Add agents
swan agent add demo upper --type shell --config "command=echo {prompt} | tr a-z A-Z"
swan agent add demo count --type shell --config "command=echo {prompt} | wc -w"

# 3. Queue tasks
swan task add demo --agent upper --input "prompt=hello from swan"
swan task add demo --agent count --input "prompt=hello from swan"

# 4. Run and watch results
swan run swarm demo
```

```
  Task ID   Agent   Status    Duration
  ────────────────────────────────────
  a3f1…     upper   success   8ms
  b9c2…     count   success   11ms
```

Preview the execution plan without running:

```bash
swan run swarm demo --dry-run
```

---

## Core Concepts

| Concept | Description |
|---|---|
| **Swarm** | A named workspace grouping related agents and tasks |
| **Agent** | A typed, reusable worker — `shell`, `http`, `claude`, or a custom plugin |
| **Task** | A unit of work assigned to one agent, with input key/value pairs |
| **Plugin** | A Python class implementing `async run(task) -> Any` |
| **Wave** | A batch of dependency-free tasks executed concurrently |

Every task carries an execution policy: `timeout`, `retries`, `retry_delay`, and `depends_on`.

→ Full walkthrough: [docs/concepts.md](docs/concepts.md)

---

## CLI Reference

```
swan swarm    create | list | show | delete | export
swan agent    add | list | show | remove | types
swan task     add | list | show | remove
swan run      swarm | task
swan result   list | show
swan plugin   list | info
```

### Common flags

| Flag | Description |
|---|---|
| `--json` | Output as JSON (all commands) |
| `--concurrency N` | Max parallel tasks (default: 10) |
| `--fail-fast` | Stop remaining waves on first failure |
| `--dry-run` | Print execution plan without running |
| `--retries N` | Retry failed tasks N times |
| `--timeout S` | Per-task timeout in seconds (default: 30) |

→ Full reference: [docs/cli-reference.md](docs/cli-reference.md)

---

## Built-in Plugins

| Plugin | What it does | Config keys | Extra install |
|---|---|---|---|
| `shell` | Runs any shell command; `{key}` placeholders are replaced from task input | `command` | — |
| `http` | Makes HTTP requests using stdlib `urllib` | `url`, `method`, `headers` | — |
| `claude` | Calls the Claude API with task input as the prompt | `model`, `max_tokens`, `system` | `pip install -e ".[claude]"` |

→ Plugin authoring guide: [docs/plugins.md](docs/plugins.md)

---

## Task Dependencies

```bash
# Wave 1: fetch  →  Wave 2: process
T1=$(swan task add myswarm --name fetch \
     --agent fetcher --input "url=https://example.com" --json | jq -r .id)

T2=$(swan task add myswarm --name process \
     --agent analyzer --input "prompt=summarize" --depends-on $T1)

swan run swarm myswarm
```

Swan performs a topological sort (Kahn's algorithm) over the task list, grouping independent tasks into **waves**. All tasks within a wave run concurrently via `asyncio.TaskGroup`. Cyclic dependencies are detected and reported before any execution begins.

```
Tasks: A, B (no deps)  →  C (needs A)  →  D (needs B and C)

Wave 1: [A, B]     concurrent
Wave 2: [C]        waits for A
Wave 3: [D]        waits for B, C
```

---

## Writing a Custom Plugin

```python
# my_plugin/plugin.py
from swan.plugins.base import AgentPlugin
from swan.core.models import Task

class MyPlugin(AgentPlugin):
    plugin_type = "mytype"

    async def setup(self) -> None:
        # Called once before the first task in a run
        pass

    async def run(self, task: Task):
        # task.input holds the key/value dict from `swan task add --input`
        # task.config holds the dict from `swan agent add --config`
        return {"result": "done"}

    async def teardown(self) -> None:
        # Called after all tasks complete or on error
        pass
```

Register via entry points in your `pyproject.toml`:

```toml
[project.entry-points."swan.plugins"]
mytype = "my_plugin.plugin:MyPlugin"
```

Install your package and `swan plugin list` will show the new type immediately.

→ Full guide: [docs/plugins.md](docs/plugins.md)

---

## Configuration

Swan works with **zero configuration**. To customise defaults, create `~/.swan/config.toml`:

```toml
[swan]
log_level           = "INFO"       # DEBUG | INFO | WARNING | ERROR
default_concurrency = 10
state_backend       = "local"      # local | redis (coming soon)

[state.local]
path = "~/.swan/state.json"
```

**Environment variables** (override the config file):

| Variable | Effect |
|---|---|
| `SWAN_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `SWAN_STATE_BACKEND` | `local` / `redis` |
| `ANTHROPIC_API_KEY` | API key for the `claude` plugin |

→ Full reference: [docs/configuration.md](docs/configuration.md)

---

## Architecture

```
CLI command
  → StateStore.load()            # read ~/.swan/state.json
  → mutate StateRoot             # add swarm / agent / task
  → StateStore.save()            # atomic write back
  ↓
swan run swarm <name>
  → SwarmRunner.run()            # load state, build plugin instances
  → topological_waves(tasks)     # Kahn's algorithm → [[wave1], [wave2], …]
  → asyncio.TaskGroup            # concurrent tasks within each wave
  → TaskExecutor.run_task()      # timeout + exponential-backoff retry
  → StateStore.save_result()     # persist TaskResult
```

**State** is a single JSON file (`~/.swan/state.json`) with atomic writes via `os.replace`. The `StateStore` interface is designed for a Redis backend (not yet implemented).

**Logging** emits two streams: Rich-formatted console output (`INFO`) and NDJSON to `~/.swan/logs/swan.log` (`DEBUG`), useful for piping into `jq`.

---

## Development

```bash
pip install -e ".[dev]"

pytest tests/ -v                          # all 23 tests (~0.2 s)
pytest tests/test_scheduler.py -v        # single file
pytest tests/test_executor.py -k retry   # single test
```

**Project layout:**

```
swan/
  cli/commands/    # one file per command group (swarm, agent, task, run, result, plugin)
  core/            # models, scheduler (topological_waves + SwarmRunner), executor
  plugins/         # AgentPlugin ABC, PluginRegistry, builtin plugins
  state/           # StateStore ABC, JSONStateStore, Redis stub
```

→ Contributing guide: [docs/contributing.md](docs/contributing.md)

---

## Roadmap

- [ ] Redis state backend for distributed swarms
- [ ] `swan worker` daemon — queue-based distributed execution
- [ ] Docker agent plugin
- [ ] Live TUI for run monitoring (`textual`)
- [ ] `--input @file.json` shorthand for bulk task input

---

## License

[MIT](LICENSE) © 2024 Ali Noor Bhatti
