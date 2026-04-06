# Contributing

Thank you for your interest in Swan! This guide covers how to set up the development environment, run tests, and submit changes.

---

## Development setup

```bash
git clone https://github.com/your-username/swan.git
cd swan

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

This installs Swan in editable mode plus `pytest` and `pytest-asyncio`.

---

## Running tests

```bash
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_scheduler.py -v

# Specific test
pytest tests/test_executor.py::test_executor_timeout -v

# With coverage report
pip install pytest-cov
pytest tests/ --cov=swan --cov-report=term-missing
```

The test suite runs in ~0.2 s and requires no network access or external services.

---

## Project structure

```
swan/
├── pyproject.toml            # package metadata, deps, entry-points
├── README.md
├── docs/                     # documentation
│   ├── concepts.md
│   ├── cli-reference.md
│   ├── plugins.md
│   ├── configuration.md
│   ├── architecture.md
│   └── contributing.md       # this file
├── swan/                     # source package
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── log.py
│   ├── cli/
│   ├── core/
│   ├── plugins/
│   └── state/
└── tests/
```

See [architecture.md](architecture.md) for a description of each module's role.

---

## Code style

- **Formatting:** no formatter is enforced; follow the existing style (4-space indent, double quotes)
- **Type hints:** use Python 3.12 syntax (`X | Y`, `list[X]`, etc.); add hints to all new public functions
- **Imports:** stdlib → third-party → internal; use `from __future__ import annotations` at the top of each file
- **Async:** all I/O must be async or dispatched via `run_in_executor`; never block the event loop

---

## Adding a new built-in plugin

1. Create `swan/plugins/builtin/my_plugin.py`:

```python
from swan.plugins.base import AgentPlugin
from swan.core.models import Task

class Plugin(AgentPlugin):
    plugin_type = "my_plugin"

    async def run(self, task: Task) -> dict:
        ...
```

2. Register it in `swan/plugins/__init__.py`:

```python
from swan.plugins.builtin import shell, http, my_plugin   # add here

def load_plugins() -> None:
    for mod in (shell, http, my_plugin):                  # add here
        PluginRegistry.register(mod.Plugin)
```

3. Declare the entry-point in `pyproject.toml`:

```toml
[project.entry-points."swan.plugins"]
my_plugin = "swan.plugins.builtin.my_plugin:Plugin"
```

4. Add tests in `tests/test_plugins.py`.

---

## Adding a new CLI command

1. Add a function to the appropriate `swan/cli/commands/*.py` file using Typer's `@app.command()` decorator
2. Keep all business logic in `swan/core/` — the command function should only parse args, call core, and render output via `swan/cli/output.py`

---

## Writing tests

Tests live in `tests/`. Use `pytest-asyncio` for async tests (the mode is set to `auto` in `pyproject.toml`).

**Async tests:**

```python
@pytest.mark.asyncio
async def test_something(store):    # `store` fixture from conftest.py
    state = await store.load()
    ...
```

**Testing plugins:**

Create a `Task` directly using the constructor (not `Task.create`) to avoid side effects:

```python
from swan.core.models import Task
from swan.core.enums import TaskStatus
from datetime import datetime

task = Task(
    id="t1", swarm_id="s1", agent_id="a1", name="test",
    input={"command": "echo hi"},
    timeout=10.0, retries=0, retry_delay=1.0,
    depends_on=[], created_at=datetime.utcnow(), status=TaskStatus.PENDING,
)
```

**Test fixtures:**

The `store` fixture in `conftest.py` creates a `JSONStateStore` backed by a temp file. Use it for any test that touches state.

---

## Submitting changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes and add tests
4. Verify all tests pass: `pytest tests/ -v`
5. Commit with a descriptive message
6. Open a pull request against `main`

**Commit message format:**

```
<type>: <short description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Examples:
- `feat: add redis state backend`
- `fix: shell plugin now falls back to agent config for command`
- `docs: add architecture diagram to architecture.md`

---

## Reporting issues

Please include:
- Swan version (`swan --version`)
- Python version (`python3 --version`)
- Operating system
- Minimal reproduction steps
- Expected vs actual behaviour
- Relevant log output (`--log-level DEBUG` is useful)
