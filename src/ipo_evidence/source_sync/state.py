from __future__ import annotations

import json
from pathlib import Path

from ipo_evidence.io import ensure_dir, read_json, write_json
from ipo_evidence.source_sync.models import SyncState


def load_sync_state(path: Path | str) -> SyncState:
    state_path = Path(path)
    if not state_path.exists():
        return SyncState()
    return SyncState.model_validate(read_json(state_path))


def save_sync_state(path: Path | str, value: SyncState | dict) -> None:
    state_path = Path(path)
    payload = value if isinstance(value, SyncState) else SyncState.model_validate(value)
    write_json(state_path, payload)


def append_jsonl_record(path: Path | str, record: dict) -> None:
    log_path = Path(path)
    ensure_dir(log_path.parent)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
