from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, value: BaseModel | dict | list) -> None:
    ensure_dir(path.parent)
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")
    else:
        payload = value
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: Iterable[BaseModel | dict]) -> None:
    ensure_dir(path.parent)
    lines: list[str] = []
    for row in rows:
        payload = row.model_dump(mode="json") if isinstance(row, BaseModel) else row
        lines.append(json.dumps(payload, ensure_ascii=False))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
