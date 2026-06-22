from __future__ import annotations

import yaml

from ipo_evidence.paths import repo_root


def load_yaml(relative_path: str) -> dict:
    path = repo_root() / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
