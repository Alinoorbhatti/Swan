# Configuration Reference

Swan works out of the box with no configuration. This page documents all available settings for when you need to customise behaviour.

---

## Config file location

Swan reads `~/.swan/config.toml` at startup. You can override the path with the `--config` global flag:

```bash
swan --config /path/to/my/config.toml swarm list
```

---

## Full config reference

```toml
[swan]
# Log level for the console (Rich) handler.
# Valid values: DEBUG, INFO, WARNING, ERROR
# Env var: SWAN_LOG_LEVEL
log_level = "INFO"

# Path for the rotating JSON log file.
# Set to an empty string to disable file logging.
log_file = "~/.swan/logs/swan.log"

# Maximum number of tasks running simultaneously within a wave.
# Can be overridden per-run with: swan run swarm myswarm --concurrency N
default_concurrency = 10

# State backend to use.
# "local"  → JSON file (default, no extra dependencies)
# "redis"  → Redis (planned; requires pip install swan[redis])
# Env var: SWAN_STATE_BACKEND
state_backend = "local"


[state.local]
# Path to the JSON state file.
# Tilde expansion is supported.
path = "~/.swan/state.json"


[state.redis]
# Redis connection URL (used when state_backend = "redis").
url = "redis://localhost:6379/0"

# Key prefix for all Swan keys in Redis.
key_prefix = "swan:"
```

---

## Environment variables

Environment variables take precedence over config file values.

| Variable | Config equivalent | Description |
|---|---|---|
| `SWAN_LOG_LEVEL` | `[swan] log_level` | Console log level |
| `SWAN_STATE_BACKEND` | `[swan] state_backend` | `local` or `redis` |
| `ANTHROPIC_API_KEY` | *(claude plugin)* | Anthropic API key for the Claude plugin |

---

## State file format

The state file (`~/.swan/state.json`) is a single JSON document:

```json
{
  "version": 1,
  "swarms": {
    "<swarm-id>": {
      "id": "...",
      "name": "myswarm",
      "description": "",
      "agent_ids": ["..."],
      "task_ids": ["..."],
      "created_at": "2026-04-06T12:00:00",
      "metadata": {}
    }
  },
  "agents": {
    "<agent-id>": {
      "id": "...",
      "swarm_id": "...",
      "name": "runner",
      "plugin_type": "shell",
      "config": { "command": "echo {prompt}" },
      "tags": [],
      "created_at": "2026-04-06T12:00:00"
    }
  },
  "tasks": {
    "<task-id>": {
      "id": "...",
      "swarm_id": "...",
      "agent_id": "...",
      "name": "say-hello",
      "input": { "prompt": "hello" },
      "timeout": 30.0,
      "retries": 0,
      "retry_delay": 1.0,
      "depends_on": [],
      "created_at": "2026-04-06T12:00:00",
      "status": "pending"
    }
  },
  "results": {
    "<task-id>": [
      {
        "task_id": "...",
        "agent_id": "...",
        "swarm_id": "...",
        "status": "success",
        "output": { "exit_code": 0, "stdout": "hello\n", "stderr": "" },
        "error": null,
        "started_at": "2026-04-06T12:00:01",
        "finished_at": "2026-04-06T12:00:01",
        "duration_ms": 8,
        "attempt": 0
      }
    ]
  }
}
```

Writes are atomic: Swan writes to a `.tmp` file first, then renames it over the real file. A crash mid-write will not corrupt the existing state.

---

## Multiple environments

Use `--store-dir` to isolate state between environments (development, staging, etc.):

```bash
swan --store-dir ~/.swan-dev  swarm create dev-swarm
swan --store-dir ~/.swan-prod swarm create prod-swarm
```

Each store directory gets its own `state.json` and `logs/` directory.

---

## Log file format

The log file uses NDJSON (one JSON object per line):

```jsonl
{"ts":"2026-04-06T12:00:01Z","level":"INFO","logger":"swan.scheduler","message":"swarm_run_started","swarm_id":"...","task_count":3,"wave_count":2}
{"ts":"2026-04-06T12:00:01Z","level":"DEBUG","logger":"swan.executor","message":"task_started","task_id":"...","agent_id":"...","attempt":0}
{"ts":"2026-04-06T12:00:01Z","level":"INFO","logger":"swan.executor","message":"task_finished","task_id":"...","status":"success","duration_ms":8}
```

Useful queries with `jq`:

```bash
# Watch failures in real time
tail -f ~/.swan/logs/swan.log | jq 'select(.level == "WARNING")'

# Find all timed-out tasks
cat ~/.swan/logs/swan.log | jq 'select(.message == "task_failed" and .status == "timeout")'

# Summarise a run by swarm
cat ~/.swan/logs/swan.log | jq 'select(.message == "swarm_run_finished") | {swarm_id, total: .total, success: .success, failed: .failed}'
```

The log file rotates at 10 MB, keeping 3 backups (`swan.log`, `swan.log.1`, `swan.log.2`).
