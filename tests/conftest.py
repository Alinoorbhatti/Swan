import pytest
import asyncio
from pathlib import Path


@pytest.fixture
def tmp_state(tmp_path) -> Path:
    return tmp_path / "state.json"


@pytest.fixture
def store(tmp_state):
    from swan.state.local import JSONStateStore
    return JSONStateStore(tmp_state)
