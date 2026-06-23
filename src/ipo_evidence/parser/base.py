from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from ipo_evidence.models import Block


class ParserOutput(BaseModel):
    markdown: str
    blocks: list[Block]
    raw_tables: list[dict] = Field(default_factory=list)
    parse_report: dict
    raw_artifacts: dict = Field(default_factory=dict)


class Parser(Protocol):
    def parse(self, pdf_path: Path) -> ParserOutput:
        raise NotImplementedError
