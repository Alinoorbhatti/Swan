# Plugin Guide

Swan's plugin system is how new agent types are added. Every agent type — including the built-ins — is a plugin. Third-party plugins install alongside Swan and are discovered automatically via Python entry-points.

---

## Built-in plugins

### `shell`

Runs an arbitrary shell command. The simplest and most flexible plugin.

**Setup:**

```bash
swan agent add myswarm runner --type shell --config "command=echo {prompt}"
```

**Task input:**

```bash
swan task add myswarm --agent runner --input "prompt=hello world"
# runs: echo hello world
```

**Agent config keys:**

| Key | Required | Description |
|---|---|---|
| `command` | Yes (if not in task input) | Shell command template. Use `{prompt}` for substitution. |

**Task input keys:**

| Key | Description |
|---|---|
| `command` | Override the agent-level command for this specific task |
| `prompt` | Substituted into `{prompt}` in the command string |
| `env` | Extra environment variables: `{"KEY": "value"}` |
| `stdin` | String piped to the process's stdin |

**Output schema:**

```json
{
  "exit_code": 0,
  "stdout": "hello world\n",
  "stderr": ""
}
```

**Examples:**

```bash
# Run a Python script
swan agent add myswarm py --type shell --config "command=python3 /path/to/script.py {prompt}"

# Pass extra env vars per task
swan task add myswarm --agent runner --input "command=printenv MY_VAR" --input 'env={"MY_VAR":"hello"}'

# Pipe stdin
swan task add myswarm --agent runner --input "command=wc -w" --input "stdin=count these words"
```

---

### `http`

Makes HTTP requests using Python's stdlib `urllib` — no extra dependencies.

**Setup:**

```bash
swan agent add myswarm fetcher --type http
```

**Task input:**

```bash
swan task add myswarm --agent fetcher --input "url=https://api.github.com/zen"
```

**Task input keys:**

| Key | Default | Description |
|---|---|---|
| `url` | required | URL to request |
| `method` | `GET` | HTTP method (GET, POST, PUT, DELETE, …) |
| `headers` | `{}` | Extra request headers as a JSON object |
| `body` | — | Request body: string or dict (dicts are JSON-encoded automatically) |
| `timeout` | `30.0` | Per-request timeout in seconds |

**Output schema:**

```json
{
  "status_code": 200,
  "headers": { "Content-Type": "application/json", "...": "..." },
  "body": { "...": "..." }
}
```

The body is decoded as JSON if possible, otherwise returned as a plain string.

**Examples:**

```bash
# POST JSON
swan task add myswarm --agent fetcher \
    --input "url=https://httpbin.org/post" \
    --input "method=POST" \
    --input 'body={"key":"value"}'

# Custom headers
swan task add myswarm --agent fetcher \
    --input "url=https://api.example.com/data" \
    --input 'headers={"Authorization":"Bearer token123"}'
```

---

### `claude`

Calls the Claude AI API via the `anthropic` Python SDK.

**Requirements:**

```bash
pip install -e ".[claude]"
export ANTHROPIC_API_KEY=sk-ant-...
```

**Setup:**

```bash
swan agent add myswarm ai --type claude --config "model=claude-haiku-4-5-20251001"
```

**Task input:**

```bash
swan task add myswarm --agent ai --input "prompt=Explain asyncio in one sentence"
```

**Agent config keys:**

| Key | Description |
|---|---|
| `model` | Default Claude model ID (e.g., `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`) |
| `api_key` | API key (alternative to `ANTHROPIC_API_KEY` env var) |
| `system` | Default system prompt applied to all tasks |
| `max_tokens` | Default max output tokens (default: `1024`) |

**Task input keys:**

| Key | Description |
|---|---|
| `prompt` | User message sent to Claude (required) |
| `model` | Override the agent-level model for this task |
| `system` | Override the system prompt |
| `max_tokens` | Override the token limit |

**Output schema:**

```json
{
  "model": "claude-haiku-4-5-20251001",
  "content": "asyncio is Python's event loop library for writing concurrent code using coroutines.",
  "input_tokens": 12,
  "output_tokens": 19,
  "stop_reason": "end_turn"
}
```

**Examples:**

```bash
# Summarize a web page (chain with http plugin via depends-on)
swan task add myswarm --agent ai \
    --input "prompt=Summarize this article in 3 bullet points" \
    --input "system=You are a concise technical writer." \
    --input "max_tokens=256"
```

---

## Writing a custom plugin

### Step 1 — Create your plugin class

```python
# my_swan_plugin/agent.py
from typing import Any, ClassVar
from swan.plugins.base import AgentPlugin
from swan.core.models import Task


class Plugin(AgentPlugin):
    plugin_type: ClassVar[str] = "my_agent"

    async def run(self, task: Task) -> Any:
        """
        Executes the task. Must return a JSON-serializable value.
        Raise any exception to signal failure (Swan catches it and records
        a TaskResult with status=failure).

        task.input  — dict of KEY=VALUE pairs from `swan task add --input`
        self.config — dict of KEY=VALUE pairs from `swan agent add --config`
        """
        message = task.input.get("message", "")
        repeat = int(self.config.get("repeat", 1))
        return {"output": message * repeat}

    async def setup(self) -> None:
        """Called once before the first task in a swarm run. Open connections here."""
        pass

    async def teardown(self) -> None:
        """Called after all tasks complete or on error. Close connections here."""
        pass
```

### Step 2 — Package it

```
my_swan_plugin/
├── pyproject.toml
└── my_swan_plugin/
    ├── __init__.py
    └── agent.py
```

`pyproject.toml`:

```toml
[project]
name = "my-swan-plugin"
version = "0.1.0"
dependencies = ["swan"]

[project.entry-points."swan.plugins"]
my_agent = "my_swan_plugin.agent:Plugin"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

### Step 3 — Install and use

```bash
pip install ./my_swan_plugin

swan agent types              # my_agent appears here
swan plugin info my_agent     # shows your docstring

swan agent add myswarm bot --type my_agent --config "repeat=3"
swan task add myswarm --agent bot --input "message=hello"
swan run swarm myswarm
```

---

## Plugin lifecycle

For each `swan run swarm` invocation, Swan creates one plugin instance per agent:

```
load_plugins()                      # discover and register all plugin classes
for each agent in swarm:
    plugin = PluginClass(agent.config)  # instantiate
    await plugin.setup()                # open connections, warm up caches, etc.

# Execute waves concurrently ...

for each plugin:
    await plugin.teardown()         # guaranteed even if tasks failed
```

The `setup` / `teardown` hooks are always paired: if `setup` succeeds, `teardown` will run even if an exception occurs during execution.

---

## Tips for robust plugins

**Always return a JSON-serializable value.**
Swan stores results in JSON. Returning a custom object will cause a serialization error at save time.

**Raise exceptions freely.**
Swan catches all exceptions from `run()` and records them as `TaskResult(status=failure, error=str(exc))`. You don't need try/except unless you want custom error messages.

**Use `self.config` for static settings, `task.input` for per-task data.**
Config is set once when the agent is created. Input is provided per task. This keeps agents reusable across many tasks.

**Honour the timeout.**
Swan enforces timeouts with `asyncio.wait_for`. Long-running operations should check for cancellation at natural boundaries (e.g., between API calls) using `await asyncio.sleep(0)`.

**Use `setup` for expensive initialisation.**
If your plugin opens a database connection or loads a model, do it in `setup` rather than `run` — `setup` is called once, `run` is called once per task.
