from __future__ import annotations

from ipo_evidence.models import TableObject


def score_table(raw_table: dict) -> float:
    has_title = bool(raw_table.get("title"))
    has_columns = bool(raw_table.get("columns"))
    has_rows = bool(raw_table.get("rows"))
    if has_title and has_columns and has_rows:
        return 0.9
    if has_columns and has_rows:
        return 0.75
    return 0.4


def normalize_page_number(raw_value: object) -> int:
    if raw_value is None or raw_value == "":
        return 1
    try:
        page_number = int(raw_value)
    except (TypeError, ValueError):
        return 1
    if page_number < 1:
        return 1
    return page_number


def extract_tables(
    raw_tables: list[dict],
    source_file: str,
    section_path: list[str],
) -> list[TableObject]:
    tables: list[TableObject] = []
    for index, raw_table in enumerate(raw_tables, start=1):
        tables.append(
            TableObject(
                table_id=f"T-{index:03d}",
                title=raw_table.get("title") or f"未命名表格 {index}",
                source_file=source_file,
                page_number=normalize_page_number(raw_table.get("page_number")),
                section_path=section_path,
                columns=list(raw_table.get("columns") or []),
                rows=list(raw_table.get("rows") or []),
                notes=list(raw_table.get("notes") or []),
                quality_score=score_table(raw_table),
            )
        )
    return tables
