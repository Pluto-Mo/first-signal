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
    doc_id_path = Path(doc_id)
    if not doc_id or doc_id_path.is_absolute() or doc_id_path.name != doc_id or ".." in doc_id:
        raise ValueError(f"Invalid doc_id: {doc_id}")

    docs_path = docs_dir().resolve()
    target_path = (docs_path / doc_id).resolve()
    if not target_path.is_relative_to(docs_path):
        raise ValueError(f"Invalid doc_id: {doc_id}")
    return target_path
