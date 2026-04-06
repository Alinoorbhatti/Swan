# Core Concepts

This page explains the mental model behind Swan: what each object is, how they relate, and how a run flows from start to finish.

---

## The Object Model

```
Swarm
 ├── Agent  (plugin_type="shell",  config={command: "..."})
 ├── Agent  (plugin_type="claude", config={model: "..."})
 └── Agent  (plugin_type="http",   config={})
      │
      ▼
   Task  (input={prompt: "hello"}, depends_on=[])
   Task  (input={url: "https://…"}, timeout=10)
   Task  (input={prompt: "summarize"}, depends_on=[task_id_1])
```

### Swarm

A **swarm** is a named workspace that groups related agents and tasks. Think of it as a project folder. Swarms are independent of each other; state is stored in `~/.swan/state.json` by default.

```bash
swan swarm create research --description "Web research pipeline"
```

### Agent

An **agent** is a typed, reusable worker registered to a swarm. Its `plugin_type` determines which plugin handles its tasks. Its `config` holds static configuration that applies to every task run on it — for example, a shell command template or a Claude model name.

```bash
# agent config is set once at creation time
swan agent add research fetcher --type http
swan agent add research summarizer --type claude --config "model=claude-haiku-4-5-20251001"
```

Agents are not task-specific. The same agent can handle many tasks, either sequentially or (for independent tasks) concurrently.

### Task

A **task** is a single unit of work assigned to one agent. Its `input` is a key/value map passed to the plugin at execution time. Tasks also carry execution policy: `timeout`, `retries`, `retry_delay`, and `depends_on`.

```bash
swan task add research \
    --agent fetcher \
    --input "url=https://example.com/article" \
    --timeout 15 \
    --retries 2
```

Tasks are stateful: they start as `pending` and end as `done` or `failed`.

### Task Result

A **task result** is an immutable record written after each execution. It contains the plugin's output (any JSON-serializable value), status (`success` / `failure` / `timeout` / `skipped`), duration, and which retry attempt produced it.

Results are stored in `~/.swan/state.json` under `results[task_id]` and can be viewed with `swan result show <task-id>`.

---

## Plugin System

A **plugin** is a Python class that knows how to run a task. All plugins inherit from `AgentPlugin`:

```python
class AgentPlugin(ABC):
    plugin_type: ClassVar[str]       # unique string identifier
    config: dict                     # from `swan agent add --config`

    async def run(self, task: Task) -> Any: ...   # must return JSON-serializable value
    async def setup(self) -> None: ...            # called once before first task
    async def teardown(self) -> None: ...         # called after all tasks
```

Swan discovers plugins via Python [entry-points](https://packaging.python.org/en/latest/specifications/entry-points/). This means any installed package can register new agent types — no changes to Swan required.

---

## Execution Model

When you run `swan run swarm myswarm`, Swan follows these steps:

### 1. Load state

All swarm agents and pending tasks are loaded from the state store.

### 2. Build the dependency graph

Swan performs a **topological sort** (Kahn's algorithm) over the task list, grouping tasks into sequential **waves**:

```
Tasks: A (no deps), B (no deps), C (depends on A), D (depends on B and C)

Wave 1: [A, B]          ← both independent, run concurrently
Wave 2: [C]             ← depends on A (already done)
Wave 3: [D]             ← depends on B and C (both done)
```

### 3. Execute wave by wave

Each wave is dispatched with `asyncio.TaskGroup`, which provides structured concurrency: if any task raises an unhandled exception, remaining tasks in the wave are cancelled cleanly.

A `Semaphore(concurrency)` limits how many tasks run simultaneously (default: 10, override with `--concurrency N`).

### 4. Per-task execution (executor)

For each task, the executor:
1. Calls `plugin.run(task)` wrapped in `asyncio.wait_for(timeout)`
2. On failure or timeout, sleeps `retry_delay * 2^attempt` seconds and retries up to `retries` times
3. Returns a `TaskResult` regardless of outcome — never propagates exceptions to the scheduler

### 5. Fail-fast mode

With `--fail-fast`, the first failed or timed-out task causes all subsequent waves to be skipped (individual tasks in that wave still complete). Skipped tasks get a result with `status=skipped`.

### 6. Persist results

All `TaskResult` objects are written to the state store after each wave.

---

## State Persistence

Swan's state is managed through a `StateStore` interface with two implementations:

| Backend | When to use |
|---|---|
| `JSONStateStore` (default) | Single-machine use; state in `~/.swan/state.json` |
| `RedisStateStore` (planned) | Multi-machine distributed swarms |

Writes use an atomic rename (`os.replace`) so a crash mid-write cannot corrupt the state file.

---

## Logging

Swan emits two log streams simultaneously:

| Stream | Format | Default level |
|---|---|---|
| Console (Rich) | Human-readable, coloured | `INFO` |
| File (`~/.swan/logs/swan.log`) | NDJSON (one JSON object per line) | `DEBUG` |

Named log events: `swarm_run_started`, `task_started`, `task_finished`, `task_failed`, `task_retrying`, `plugin_loaded`, `swarm_run_finished`, `state_saved`.

The file log is useful for auditing or piping into tools like `jq`:

```bash
tail -f ~/.swan/logs/swan.log | jq 'select(.event == "task_failed")'
```
