from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings

_LOCK = threading.RLock()
DATA_DIR = settings.data_dir
STATE_FILE = DATA_DIR / "state.json"
EVENT_FILE = DATA_DIR / "events.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_state() -> dict[str, Any]:
    with _LOCK:
        _ensure()
        if not STATE_FILE.exists():
            return {"version": 1, "agents": [], "tasks": [], "approvals": [], "project": None}
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            backup = STATE_FILE.with_suffix(".corrupt.json")
            try:
                os.replace(STATE_FILE, backup)
            except OSError:
                pass
            raise RuntimeError(f"State file could not be read; preserved at {backup}: {exc}") from exc


def write_state(state: dict[str, Any]) -> None:
    with _LOCK:
        _ensure()
        payload = json.dumps(state, indent=2, ensure_ascii=False)
        fd, temp_name = tempfile.mkstemp(prefix="state-", suffix=".tmp", dir=DATA_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if STATE_FILE.exists():
                backup = STATE_FILE.with_suffix(".json.bak")
                backup.write_text(STATE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            os.replace(temp_name, STATE_FILE)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


def append_event(kind: str, message: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    event = {"id": f"evt-{datetime.now(timezone.utc).timestamp():.6f}", "at": now_iso(),
             "kind": kind, "message": message, "metadata": metadata or {}}
    with _LOCK:
        _ensure()
        with EVENT_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_events(limit: int = 100) -> list[dict[str, Any]]:
    with _LOCK:
        _ensure()
        if not EVENT_FILE.exists():
            return []
        lines = EVENT_FILE.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 1000)):]
        return [json.loads(line) for line in lines if line.strip()]
