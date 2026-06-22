from __future__ import annotations

from pathlib import Path

from ipo_evidence.models import Block
from ipo_evidence.parser.base import ParserOutput


class ApiStubParser:
    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path

    def parse(self, pdf_path: Path) -> ParserOutput:
        markdown = self.fixture_path.read_text(encoding="utf-8")
        blocks: list[Block] = []
        block_number = 1
        current_page = 1
        for paragraph in [part.strip() for part in markdown.split("\n\n") if part.strip()]:
            blocks.append(
                Block(
                    block_id=f"B-{block_number:06d}",
                    page_number=current_page,
                    text=paragraph,
                    section_path=[],
                )
            )
            block_number += 1
            current_page += 1

        raw_tables = [
            {
                "title": "产品收入结构表",
                "page_number": 3,
                "columns": ["产品", "2023年收入", "占比"],
                "rows": [
                    ["智能控制器", "12000万元", "45.2%"],
                    ["智能终端", "9800万元", "36.9%"],
                ],
                "notes": [],
            }
        ]

        parse_report = {
            "source_file": pdf_path.name,
            "quality_status": "safe_to_use",
            "page_count": len(blocks),
            "garbled_ratio": 0.0,
            "raw_table_count": len(raw_tables),
        }
        return ParserOutput(
            markdown=markdown,
            blocks=blocks,
            raw_tables=raw_tables,
            parse_report=parse_report,
        )
