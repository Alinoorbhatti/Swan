from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path

# Named log events
SWARM_RUN_STARTED  = "swarm_run_started"
SWARM_RUN_FINISHED = "swarm_run_finished"
TASK_STARTED       = "task_started"
TASK_FINISHED      = "task_finished"
TASK_FAILED        = "task_failed"
TASK_RETRYING      = "task_retrying"
PLUGIN_LOADED      = "plugin_loaded"
STATE_SAVED        = "state_saved"


class JsonFormatter(logging.Formatter):
    """Emits one JSON object per line (NDJSON)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields attached to the record
        for key, val in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "taskName",
            ):
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    root = logging.getLogger("swan")
    root.setLevel(level)
    root.handlers.clear()  # idempotent re-configuration

    try:
        from rich.logging import RichHandler
        console_handler: logging.Handler = RichHandler(
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
    except ImportError:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    console_handler.setLevel(level)
    root.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10_000_000, backupCount=3
        )
        file_handler.setFormatter(JsonFormatter())
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
