<p align="center">
  <img src="docs/logo.svg" alt="Swan — Agent Orchestration" width="380"/>
</p>

> Orchestrate swarms of AI agents and CLI tools from your terminal.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-23%20passing-brightgreen)](#development)

Swan is a lightweight Python CLI for running **swarms of agents** — shell commands, HTTP endpoints, Claude AI models, or any custom plugin — concurrently, with dependency ordering, retry logic, and structured logging. No config files required to get started.

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
git clone https://github.com/your-username/swan.git
cd swan
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Optional extras:

```bash
pip install -e ".[claude]"   # Claude AI agent (needs ANTHROPIC_API_KEY)
pip install -e ".[dev]"      # pytest + pytest-asyncio for development
```

---

## 60-second demo

```bash
# Create a swarm
swan swarm create demo

# Add two shell agents
swan agent add demo upper  --type shell --config "command=echo {prompt} | tr a-z A-Z"
swan agent add demo count  --type shell --config "command=echo {prompt} | wc -w"

# Queue tasks
swan task add demo --agent upper --input "prompt=hello from swan"
swan task add demo --agent count --input "prompt=hello from swan"

# Run concurrently and see results
swan run swarm demo
```

```
  Task ID        Agent   Status    Duration
  ─────────────────────────────────────────
  a3f1…          upper   success   8ms
  b9c2…          count   success   11ms
```

---

## Core concepts

| Concept | Description |
|---|---|
| **Swarm** | A named collection of agents and tasks |
| **Agent** | A typed worker: `shell`, `http`, `claude`, or a custom plugin |
| **Task** | A unit of work assigned to one agent with input key/value pairs |
| **Plugin** | A Python class that implements `async run(task) -> Any` |
| **Wave** | A batch of dependency-free tasks executed concurrently |

→ See [docs/concepts.md](docs/concepts.md) for a detailed walkthrough.

---

## CLI overview

```
swan swarm   create | list | show | delete | export
swan agent   add | list | show | remove | types
swan task    add | list | show | remove
swan run     swarm | task
swan result  list | show
swan plugin  list | info
```

→ Full reference: [docs/cli-reference.md](docs/cli-reference.md)

---

## Built-in plugins

| Plugin | What it does | Extra install needed? |
|---|---|---|
| `shell` | Runs any shell command | No |
| `http` | Makes HTTP requests (stdlib `urllib`) | No |
| `claude` | Calls Claude AI API | `pip install -e ".[claude]"` |

→ Plugin authoring guide: [docs/plugins.md](docs/plugins.md)

---

## Task dependencies

```bash
# fetch runs first; process waits for it
T1=$(swan task add myswarm --name fetch   --agent fetcher  --input "url=https://example.com" --json | jq -r .id)
T2=$(swan task add myswarm --name process --agent analyzer --input "prompt=summarize" --depends-on $T1)

swan run swarm myswarm  # Wave 1: fetch  →  Wave 2: process
```

Swan resolves dependencies with a topological sort (Kahn's algorithm) and executes each wave with `asyncio.TaskGroup`.

---

## Configuration

Swan works with zero configuration. To customise, create `~/.swan/config.toml`:

```toml
[swan]
log_level           = "INFO"
default_concurrency = 10
state_backend       = "local"   # or "redis" (coming soon)

[state.local]
path = "~/.swan/state.json"
```

Environment variables (override config file):

| Variable | Effect |
|---|---|
| `SWAN_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `SWAN_STATE_BACKEND` | `local` / `redis` |
| `ANTHROPIC_API_KEY` | API key for the Claude plugin |

→ Full config reference: [docs/configuration.md](docs/configuration.md)

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v          # 23 tests, ~0.2 s
```

→ [docs/contributing.md](docs/contributing.md)

---

## Roadmap

- [ ] Redis state backend for distributed swarms
- [ ] `swan worker` daemon (queue-based distributed execution)
- [ ] Docker agent plugin
- [ ] Live TUI for run monitoring
- [ ] `--input @file.json` shorthand

---

## License

[MIT](LICENSE)
