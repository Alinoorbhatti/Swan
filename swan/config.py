from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


_DEFAULT_CONFIG_DIR = Path.home() / ".swan"
_DEFAULT_STATE_FILE = _DEFAULT_CONFIG_DIR / "state.json"
_DEFAULT_LOG_FILE   = _DEFAULT_CONFIG_DIR / "logs" / "swan.log"
_CONFIG_FILE        = _DEFAULT_CONFIG_DIR / "config.toml"


@dataclass(frozen=True)
class Settings:
    log_level: str = "INFO"
    log_file: Path | None = _DEFAULT_LOG_FILE
    default_concurrency: int = 10
    state_backend: str = "local"          # "local" | "redis"
    state_path: Path = _DEFAULT_STATE_FILE
    redis_url: str = "redis://localhost:6379/0"
    redis_key_prefix: str = "swan:"
    config_dir: Path = _DEFAULT_CONFIG_DIR

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Settings":
        raw: dict = {}

        path = config_path or _CONFIG_FILE
        if path.exists():
            with open(path, "rb") as fh:
                raw = tomllib.load(fh)

        swan_section  = raw.get("swan", {})
        local_section = raw.get("state", {}).get("local", {})
        redis_section = raw.get("state", {}).get("redis", {})

        def _env(key: str, default: str) -> str:
            return os.environ.get(key, default)

        log_level = _env("SWAN_LOG_LEVEL", swan_section.get("log_level", "INFO"))
        log_file_raw = swan_section.get("log_file", str(_DEFAULT_LOG_FILE))
        log_file: Path | None = Path(log_file_raw).expanduser() if log_file_raw else None

        state_backend = _env(
            "SWAN_STATE_BACKEND",
            swan_section.get("state_backend", "local"),
        )
        state_path_raw = local_section.get("path", str(_DEFAULT_STATE_FILE))
        state_path = Path(state_path_raw).expanduser()

        return cls(
            log_level=log_level.upper(),
            log_file=log_file,
            default_concurrency=int(swan_section.get("default_concurrency", 10)),
            state_backend=state_backend,
            state_path=state_path,
            redis_url=redis_section.get("url", "redis://localhost:6379/0"),
            redis_key_prefix=redis_section.get("key_prefix", "swan:"),
            config_dir=_DEFAULT_CONFIG_DIR,
        )

    def ensure_dirs(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
