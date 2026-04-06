# CLI Reference

All commands support `--help` for inline documentation.

## Global flags

These flags apply to every command and must be placed **before** the subcommand:

```bash
swan [GLOBAL FLAGS] <command> ...
```

| Flag | Default | Description |
|---|---|---|
| `--version` / `-V` | — | Print version and exit |
| `--log-level TEXT` | `INFO` | Console log level: `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--config PATH` | `~/.swan/config.toml` | Path to a custom config file |
| `--store-dir PATH` | `~/.swan` | Override the directory containing `state.json` |

**Example:**

```bash
swan --log-level DEBUG --store-dir /tmp/test-store swarm list
```

---

## ID resolution

All commands that accept a swarm/agent/task reference try to resolve it in this order:

1. Exact full ID (hex UUID, 32 chars)
2. Unambiguous ID prefix (e.g., `a3f1b2`)
3. Name (exact match)

If a prefix matches multiple objects, Swan prints an error and exits.

---

## `swan swarm`

### `swan swarm create <name>`

Create a new swarm.

```bash
swan swarm create myswarm
swan swarm create myswarm --description "Web scraping pipeline"
```

| Option | Description |
|---|---|
| `--description TEXT` | Optional human-readable description |
| `--json` | Output created swarm as JSON |

### `swan swarm list`

List all swarms in a table.

```bash
swan swarm list
swan swarm list --json
```

### `swan swarm show <id|name>`

Show detailed information about a swarm.

```bash
swan swarm show myswarm
swan swarm show a3f1b2 --json
```

### `swan swarm delete <id|name>`

Delete a swarm along with all its agents, tasks, and results.

```bash
swan swarm delete myswarm
swan swarm delete myswarm --force    # skip confirmation prompt
```

### `swan swarm export <id|name>`

Export a swarm definition (swarm + agents + tasks) as JSON.

```bash
swan swarm export myswarm                  # print to stdout
swan swarm export myswarm --out swarm.json # write to file
```

The exported file can be inspected or backed up. Import is on the roadmap.

---

## `swan agent`

### `swan agent add <swarm> <name>`

Add an agent to a swarm.

```bash
swan agent add myswarm runner --type shell --config "command=echo {prompt}"
swan agent add myswarm ai     --type claude --config "model=claude-haiku-4-5-20251001"
swan agent add myswarm fetcher --type http
```

| Option | Required | Description |
|---|---|---|
| `--type` / `-t TEXT` | Yes | Plugin type (e.g., `shell`, `http`, `claude`) |
| `--config` / `-c KEY=VALUE` | No | Plugin config pairs; repeat for multiple |
| `--tag TEXT` | No | Tag for grouping; repeat for multiple |
| `--json` | No | Output created agent as JSON |

Config values are parsed as JSON first (so `--config "max_tokens=512"` stores an integer), then as a plain string if JSON parsing fails.

### `swan agent list <swarm>`

List agents in a swarm.

```bash
swan agent list myswarm
swan agent list myswarm --json
```

### `swan agent show <id|name>`

Show agent details including config.

```bash
swan agent show runner
swan agent show a3f1b2 --json
```

### `swan agent remove <id|name>`

Remove an agent from its swarm.

```bash
swan agent remove runner
swan agent remove runner --force
```

### `swan agent types`

List all registered plugin types (built-ins + any installed third-party plugins).

```bash
swan agent types
```

---

## `swan task`

### `swan task add <swarm>`

Add a task to a swarm.

```bash
swan task add myswarm --agent runner --input "prompt=hello world"
swan task add myswarm --agent fetcher --input "url=https://example.com" --timeout 10
swan task add myswarm --agent ai --input "prompt=summarize" --depends-on <task-id>
```

| Option | Default | Description |
|---|---|---|
| `--agent` / `-a TEXT` | required | Agent ID or name |
| `--name` / `-n TEXT` | `task-N` | Human-readable task name |
| `--input` / `-i KEY=VALUE` | — | Input pairs; repeat for multiple |
| `--timeout FLOAT` | `30.0` | Timeout in seconds (`0` = no limit) |
| `--retries INT` | `0` | Max retry attempts |
| `--depends-on TEXT` | — | Task ID this task depends on; repeat for multiple |
| `--json` | — | Output created task as JSON |

Input values follow the same JSON-then-string parsing as config values.

### `swan task list <swarm>`

List tasks in a swarm.

```bash
swan task list myswarm
swan task list myswarm --status pending
swan task list myswarm --json
```

Valid status values: `pending`, `running`, `done`, `failed`, `skipped`.

### `swan task show <id|prefix>`

Show task details.

```bash
swan task show a3f1b2
swan task show my-task --json
```

### `swan task remove <id|prefix>`

Remove a task and its results.

```bash
swan task remove a3f1b2
swan task remove my-task --force
```

---

## `swan run`

### `swan run swarm <id|name>`

Run all pending tasks in a swarm.

```bash
swan run swarm myswarm
swan run swarm myswarm --concurrency 4
swan run swarm myswarm --fail-fast
swan run swarm myswarm --dry-run      # show wave plan without executing
swan run swarm myswarm --json         # output results as JSON
```

| Option | Default | Description |
|---|---|---|
| `--concurrency` / `-c INT` | `10` | Max tasks running simultaneously |
| `--dry-run` | false | Print execution wave plan without running |
| `--fail-fast` | false | Stop after first failed/timed-out task |
| `--json` | false | Print results as JSON |

**Dry-run output example:**

```
Dry run — swarm: myswarm (a3f1b2…)

   Wave 1 (2 tasks)
   Task ID    Name     Agent     Plugin   Depends on
   a3f1b2…    fetch    fetcher   http     —
   b9c2d3…    greet    runner    shell    —

   Wave 2 (1 task)
   Task ID    Name      Agent       Plugin   Depends on
   c4e5f6…    analyze   analyzer    claude   a3f1b2…
```

### `swan run task <id|prefix>`

Run a single task (ignores dependencies).

```bash
swan run task a3f1b2
swan run task my-task --json
```

---

## `swan result`

### `swan result list <swarm>`

List all results for a swarm.

```bash
swan result list myswarm
swan result list myswarm --status failure
swan result list myswarm --json
```

### `swan result show <task-id>`

Show the full result for a task, including output payload.

```bash
swan result show a3f1b2
swan result show a3f1b2 --attempt 0   # specific retry attempt
swan result show a3f1b2 --json        # machine-readable
```

---

## `swan plugin`

### `swan plugin list`

List all registered plugin types with their class and module.

```bash
swan plugin list
```

### `swan plugin info <type>`

Show detailed information and the docstring for a plugin.

```bash
swan plugin info shell
swan plugin info claude
```

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Command-line error (bad argument, not found, etc.) |
| `2` | Typer/Click internal error |

Note: task execution failures do **not** cause a non-zero CLI exit code — they are recorded as `TaskResult` objects with `status=failure`. Use `--json` and `jq` to detect failures in scripts:

```bash
swan run swarm myswarm --json | jq 'any(.[]; .status != "success")'
```
