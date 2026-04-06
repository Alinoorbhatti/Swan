# Swan 🦢

**Orchestrate swarms of AI agents and CLI tools from your terminal.**

Swan lets you create named swarms of agents, assign tasks, run them concurrently, and collect results — all from an intuitive CLI. It ships with a plugin system so you can add any agent type (shell commands, HTTP endpoints, Claude AI, and more) without touching Swan's core.

---

## Features

- **Swarm management** — create, list, show, delete named swarms
- **Agent plugins** — built-in `shell`, `http`, and `claude` plugins; add your own via Python entry-points
- **Concurrent execution** — asyncio-powered parallel task dispatch with configurable concurrency limit
- **Dependency graphs** — declare task dependencies for ordered pipeline execution
- **Retry & timeout** — per-task timeout and exponential-backoff retry
- **Structured logging** — Rich console output + NDJSON file logs at `~/.swan/logs/swan.log`
- **JSON output** — every command supports `--json` for scripting/piping
- **Dry-run mode** — preview the execution wave plan before running
- **Extensible state** — local JSON store by default; Redis backend architecture built in

---

## Installation

**Requirements:** Python 3.12+

```bash
git clone https://github.com/your-username/swan.git
cd swan
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

For the Claude AI plugin:
```bash
pip install -e ".[claude]"
export ANTHROPIC_API_KEY=your_key_here
```

For development (includes pytest):
```bash
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Create a swarm
swan swarm create myswarm --description "My first swarm"

# Add shell agents
swan agent add myswarm greeter  --type shell --config "command=echo Hello, {prompt}!"
swan agent add myswarm reverser --type shell --config "command=echo {prompt} | rev"

# Assign tasks
swan task add myswarm --agent greeter  --input "prompt=World"
swan task add myswarm --agent reverser --input "prompt=World"

# Run all tasks concurrently
swan run swarm myswarm

# View results
swan result list myswarm
```

---

## CLI Reference

### Swarms

```
swan swarm create <name> [--description TEXT]
swan swarm list
swan swarm show <id|name>
swan swarm delete <id|name> [--force]
swan swarm export <id|name> [--out FILE]
```

### Agents

```
swan agent add <swarm> <name> --type TYPE [--config KEY=VALUE ...]
swan agent list <swarm>
swan agent show <id|name>
swan agent remove <id|name> [--force]
swan agent types               # list all registered plugin types
```

### Tasks

```
swan task add <swarm> --agent <id|name> --input KEY=VALUE ... [--name NAME] [--timeout N] [--retries N] [--depends-on ID ...]
swan task list <swarm> [--status STATUS]
swan task show <id|prefix>
swan task remove <id|prefix> [--force]
```

### Run

```
swan run swarm <id|name> [--concurrency N] [--dry-run] [--fail-fast]
swan run task <id|prefix>
```

### Results

```
swan result list <swarm> [--status STATUS]
swan result show <task-id>
```

### Plugins

```
swan plugin list
swan plugin info <type>
```

### Global flags

```
swan --version
swan --log-level DEBUG|INFO|WARNING|ERROR
swan --config PATH         # custom config.toml
swan --store-dir PATH      # override state directory
```

---

## Built-in Plugins

### `shell` — Run shell commands

```bash
swan agent add myswarm runner --type shell --config "command=echo {prompt}"
swan task add myswarm --agent runner --input "prompt=hello world"
```

**Agent config keys:**
| Key | Description |
|---|---|
| `command` | Shell command template (use `{prompt}` for task input substitution) |

**Task input keys:**
| Key | Description |
|---|---|
| `command` | Override the agent-level command for this task |
| `prompt` | Substituted into `{prompt}` in the command |
| `env` | Extra environment variables (`{"KEY": "val"}`) |
| `stdin` | Data piped to the process stdin |

**Output:** `{ exit_code, stdout, stderr }`

---

### `http` — Make HTTP requests

```bash
swan agent add myswarm fetcher --type http
swan task add myswarm --agent fetcher --input "url=https://api.github.com/zen"
```

**Task input keys:**
| Key | Default | Description |
|---|---|---|
| `url` | required | URL to request |
| `method` | `GET` | HTTP method |
| `headers` | `{}` | Extra headers |
| `body` | — | String or dict (dicts auto-JSON-encoded) |
| `timeout` | `30.0` | Per-request timeout in seconds |

**Output:** `{ status_code, headers, body }`

---

### `claude` — Claude AI

```bash
pip install -e ".[claude]"
export ANTHROPIC_API_KEY=sk-ant-...

swan agent add myswarm ai --type claude --config "model=claude-haiku-4-5-20251001"
swan task add myswarm --agent ai --input "prompt=Summarize asyncio in one sentence"
```

**Agent config keys:**
| Key | Description |
|---|---|
| `model` | Default Claude model ID |
| `api_key` | API key (or set `ANTHROPIC_API_KEY`) |
| `system` | Default system prompt |

**Task input keys:** `prompt`, `model`, `system`, `max_tokens`

**Output:** `{ model, content, input_tokens, output_tokens, stop_reason }`

---

## Task Dependencies

Chain tasks into pipelines using `--depends-on`:

```bash
# Create two sequential tasks: fetch → process
swan task add myswarm --name fetch   --agent fetcher  --input "url=https://example.com"
swan task add myswarm --name process --agent analyzer --input "prompt=summarize" \
    --depends-on <fetch-task-id>

# Swan automatically executes them in order
swan run swarm myswarm
```

Swan uses a topological sort (Kahn's algorithm) to group tasks into execution waves. Tasks within a wave run concurrently; waves run sequentially.

---

## Plugin System

Swan discovers agent plugins via Python package entry-points. To create a third-party plugin:

**1. Implement `AgentPlugin`:**

```python
# my_swan_plugin/agent.py
from swan.plugins.base import AgentPlugin
from swan.core.models import Task

class Plugin(AgentPlugin):
    plugin_type = "my_agent"

    async def run(self, task: Task) -> dict:
        # task.input contains the key/value pairs from `swan task add --input`
        # self.config contains the key/value pairs from `swan agent add --config`
        return {"result": "done"}

    async def setup(self) -> None:
        pass  # called once before the first task

    async def teardown(self) -> None:
        pass  # called after all tasks complete
```

**2. Register via entry-point in `pyproject.toml`:**

```toml
[project.entry-points."swan.plugins"]
my_agent = "my_swan_plugin.agent:Plugin"
```

**3. Install and use:**

```bash
pip install ./my_swan_plugin
swan agent types           # my_agent appears here
swan agent add myswarm bot --type my_agent
```

---

## Configuration

Swan reads `~/.swan/config.toml`:

```toml
[swan]
log_level = "INFO"
log_file  = "~/.swan/logs/swan.log"
default_concurrency = 10
state_backend = "local"   # "local" | "redis" (redis: coming soon)

[state.local]
path = "~/.swan/state.json"
```

Environment variables override config file values:
- `SWAN_LOG_LEVEL` — log level
- `SWAN_STATE_BACKEND` — state backend

---

## Architecture

```
swan/
├── cli/           # Typer commands (presentation layer only)
│   ├── main.py    # root app, global flags, store/settings wiring
│   ├── output.py  # Rich table/panel helpers
│   └── commands/  # swarm, agent, task, run, result, plugin
├── core/
│   ├── models.py    # Swarm, Agent, Task, TaskResult dataclasses
│   ├── executor.py  # per-task timeout + retry
│   └── scheduler.py # topological sort → asyncio.TaskGroup wave dispatch
├── plugins/
│   ├── base.py      # AgentPlugin ABC
│   ├── registry.py  # PluginRegistry singleton
│   └── builtin/     # shell, http, claude
└── state/
    ├── base.py      # StateStore ABC
    ├── local.py     # JSON file store (atomic writes)
    └── backends/    # redis_backend.py (stub, coming soon)
```

**Data flow:**

```
swan run swarm myswarm
  → load state (swarms, agents, tasks)
  → topological_waves(tasks)       # dependency sort
  → for each wave:
        asyncio.TaskGroup(          # structured concurrency
            executor.run_task(task, plugin)  # timeout + retry
            for task in wave
        )
  → persist TaskResults
  → display results table
```

---

## Development

```bash
# Run tests
pytest tests/ -v

# Run a specific test
pytest tests/test_scheduler.py -v

# Check coverage
pip install pytest-cov
pytest tests/ --cov=swan --cov-report=term-missing
```

Tests cover: models, state persistence, executor (retry/timeout), scheduler (DAG/waves), shell plugin.

---

## Roadmap

- [ ] Redis state backend for distributed multi-process swarms
- [ ] `swan worker` daemon — pull tasks from a queue
- [ ] Docker agent plugin (`aiodocker`)
- [ ] Web UI / TUI for live run monitoring
- [ ] Swarm import from JSON export
- [ ] `swan task add --input @file.json` shorthand

---

## License

MIT
