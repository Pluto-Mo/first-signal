from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return repo_root() / "data"


def inbox_dir() -> Path:
    return data_dir() / "inbox"


def docs_dir() -> Path:
    return data_dir() / "docs"


def doc_dir(doc_id: str) -> Path:
    return docs_dir() / doc_id
