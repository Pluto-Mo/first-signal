from __future__ import annotations

from html.parser import HTMLParser
import re

from ipo_evidence.models import Block, EvidenceItem, EvidencePacket, QualityStatus, TableObject
from ipo_evidence.section_mapper import normalize_heading


_TOC_DOT_PATTERN = re.compile(r"[.．·•]{3,}\s*\d+")
_TOC_MULTI_SECTION_PATTERN = re.compile(r"第[一二三四五六七八九十百零]+节.+第[一二三四五六七八九十百零]+节")
_FACT_TEXT_PATTERNS = (
    "公司主要从事",
    "主要产品",
    "主要业务",
    "报告期内",
    "销售",
    "收入",
    "客户",
    "供应商",
    "研发费用",
    "现金流量",
    "风险",
    "治理",
    "董事会",
    "关联交易",
    "关联方",
    "募集资金",
)
_SECTION_CANONICAL_PATTERNS = (
    ("risks", ("风险因素", "风险")),
    ("financials", ("财务会计信息", "管理层讨论与分析", "财务", "研发费用", "现金流量")),
    ("governance", ("公司治理", "治理", "董事会", "股东会", "监事会")),
    ("related_party", ("关联交易", "关联方")),
    ("use_of_proceeds", ("募集资金运用", "募集资金用途")),
    ("business_and_product", ("业务与技术", "业务和技术", "主营业务", "主要产品", "产品或服务")),
    ("about_company", ("发行人基本情况", "发行人概况", "公司设立")),
)
_EXCLUDED_SECTION_PATTERNS = (
    "释义",
    "附件",
    "发行人声明",
)
_COVER_SECTION_PATTERNS = ("招股说明书",)
_HTML_TABLE_PATTERN = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_BLOCK_PATTERN = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)
_HIGH_VALUE_TABLE_PATTERNS = (
    "营业收入",
    "主营业务收入",
    "毛利率",
    "研发费用",
    "研发投入",
    "销售费用",
    "销售费用率",
    "现金流量净额",
    "应收账款",
    "存货",
    "市场规模",
    "市占率",
    "市场份额",
    "募集资金",
    "占比",
)
_LOW_SIGNAL_TEXT_PATTERNS = (
    "参见本招股说明书",
    "详见本招股说明书",
    "如下表所示",
    "具体情况如下",
)
_MIN_TEXT_EVIDENCE_SCORE = 2
_HIGH_INFORMATION_TEXT_PATTERNS = (
    "产品服务体系",
    "规模化应用",
    "核心能力",
    "解决方案",
    "技术体系",
    "业务模式",
    "研发费用",
    "现金流量",
    "治理制度",
    "关联交易",
    "募集资金",
    "客户集中度",
)
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


class _HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag == "tr":
            self._current_row = []
        if tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_row is not None and self._current_cell is not None:
            value = " ".join("".join(self._current_cell).split())
            self._current_row.append(value)
            self._current_cell = None
        if tag == "tr" and self._current_row is not None:
            if any(cell for cell in self._current_row):
                self.rows.append(self._current_row)
            self._current_row = None


def _parse_html_table(html: str) -> tuple[list[str], list[list[str]]] | None:
    if "rowspan" in html.lower() or "colspan" in html.lower():
        return None
    parser = _HtmlTableParser()
    parser.feed(html)
    rows = [row for row in parser.rows if any(cell for cell in row)]
    if len(rows) < 2:
        return None

    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    columns = normalized[0]
    data_rows = normalized[1:]
    if not any(column for column in columns):
        return None
    return columns, data_rows


def _is_high_value_table(columns: list[str], rows: list[list[str]], section_path: list[str]) -> bool:
    text = " ".join(section_path + columns + [cell for row in rows[:8] for cell in row])
    if not any(pattern in text for pattern in _HIGH_VALUE_TABLE_PATTERNS):
        return False
    numeric_cells = [
        cell
        for row in rows
        for cell in row
        if _number_from_text(cell) is not None
    ]
    return len(numeric_cells) >= 3


def _html_tables_from_block(block: Block, source_file: str) -> list[TableObject]:
    tables: list[TableObject] = []
    for table_index, match in enumerate(_HTML_TABLE_BLOCK_PATTERN.finditer(block.text), start=1):
        parsed = _parse_html_table(match.group(0))
        if parsed is None:
            continue
        columns, rows = parsed
        if not _is_high_value_table(columns, rows, block.section_path):
            continue
        title = block.section_path[-1] if block.section_path else f"HTML表格{table_index}"
        tables.append(
            TableObject(
                table_id=f"HT-{block.block_id}-{table_index:02d}",
                title=title,
                source_file=source_file,
                page_number=block.page_number,
                section_path=block.section_path or ["未识别章节"],
                columns=columns,
                rows=rows[:12],
                quality_score=0.8,
            )
        )
    return tables


def _split_heading_and_body(block: Block) -> tuple[list[str], str]:
    lines = [line.strip() for line in block.text.splitlines() if line.strip()]
    if len(lines) < 2:
        return block.section_path, block.text

    heading = normalize_heading(lines[0])
    if not heading:
        return block.section_path, block.text

    _, title = heading
    body = "\n".join(lines[1:]).strip()
    if not body:
        return block.section_path, block.text

    section_path = block.section_path.copy()
    if not section_path or title not in section_path:
        section_path.append(title)
    return section_path, body


def _looks_like_directory(text: str) -> bool:
    compact = " ".join(text.split())
    return bool(_TOC_DOT_PATTERN.search(compact) or _TOC_MULTI_SECTION_PATTERN.search(compact))


def _is_heading_only(text: str) -> bool:
    return normalize_heading(text) is not None


def _is_fact_like_text(text: str) -> bool:
    return any(pattern in text for pattern in _FACT_TEXT_PATTERNS)


def _is_excluded_section(section_path: list[str]) -> bool:
    if any(
        excluded in section
        for section in section_path
        for excluded in _EXCLUDED_SECTION_PATTERNS
    ):
        return True
    return len(section_path) == 1 and any(
        cover in section_path[0] for cover in _COVER_SECTION_PATTERNS
    )


def _is_html_table_block(text: str) -> bool:
    return bool(_HTML_TABLE_PATTERN.search(text))


def _infer_canonical_section(section_path: list[str], text: str) -> str:
    haystack = " ".join(section_path + [text])
    for canonical_key, patterns in _SECTION_CANONICAL_PATTERNS:
        if any(pattern in haystack for pattern in patterns):
            return canonical_key
    return "about_company"


def _score_text_block(block: Block) -> int:
    score = 0
    text = block.text
    if any(pattern in text for pattern in _FACT_TEXT_PATTERNS):
        score += 2
    if any(pattern in text for pattern in _HIGH_INFORMATION_TEXT_PATTERNS):
        score += 2
    if len(text) >= 30:
        score += 1
    if any(pattern in text for pattern in _LOW_SIGNAL_TEXT_PATTERNS):
        score -= 3
    if text.endswith("如下：") or text.endswith("如下。"):
        score -= 2
    return score


def _number_from_text(value: str) -> float | None:
    match = _NUMBER_PATTERN.search(value.replace(",", ""))
    if not match:
        return None
    return float(match.group(0))


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _unit_from_values(values: list[str]) -> str:
    for value in values:
        stripped = value.strip()
        if stripped.endswith("%"):
            return "%"
        if stripped.endswith("万元"):
            return "万元"
        if stripped.endswith("亿元"):
            return "亿元"
        if stripped.endswith("元"):
            return "元"
    return ""


def _table_row_fields(table: TableObject, row: list[str]) -> dict[str, str]:
    return {
        table.columns[index]: row[index]
        for index in range(min(len(table.columns), len(row)))
        if table.columns[index] and row[index]
    }


def _table_subject(fields: dict[str, str], fallback: str) -> str:
    for key in ("产品", "项目", "业务指标", "应用领域", "公司名称", "客户名称", "类别", "名称"):
        if fields.get(key):
            return fields[key]
    return fallback


def _append_table_row_items(
    items: list[EvidenceItem],
    next_id: int,
    table: TableObject,
) -> int:
    for row_number, row in enumerate(table.rows, start=1):
        fields = _table_row_fields(table, row)
        if not fields:
            continue
        subject = _table_subject(fields, f"第{row_number}行")
        items.append(
            EvidenceItem(
                evidence_id=f"E-{next_id:03d}",
                canonical_section=_infer_canonical_section(table.section_path, table.title),
                claim_summary=f"{table.title}中，{subject}对应数据为：{fields}",
                source_type="table_fact",
                source_file=table.source_file,
                page_number=table.page_number,
                table_id=table.table_id,
                table_title=table.title,
                section_path=table.section_path or ["未识别章节"],
                fields=fields,
                quality_status=QualityStatus.safe_to_use,
            )
        )
        next_id += 1
    return next_id


def _append_table_summary_items(
    items: list[EvidenceItem],
    next_id: int,
    table: TableObject,
) -> int:
    if len(table.rows) < 2 or not table.columns:
        return next_id

    first_column = table.columns[0]
    numeric_columns = [
        column_index
        for column_index, column_name in enumerate(table.columns)
        if column_index > 0
        and all(
            column_index < len(row) and _number_from_text(row[column_index]) is not None
            for row in table.rows
        )
    ]
    if not numeric_columns:
        return next_id

    fields: dict[str, str] = {
        "覆盖项目": "、".join(row[0] for row in table.rows if row and row[0])
    }
    for column_index in numeric_columns:
        column_name = table.columns[column_index]
        raw_values = [
            row[column_index]
            for row in table.rows
            if column_index < len(row)
        ]
        values = [
            _number_from_text(value)
            for value in raw_values
        ]
        numeric_values = [value for value in values if value is not None]
        total = sum(numeric_values)
        fields[f"{column_name}合计"] = f"{_format_number(total)}{_unit_from_values(raw_values)}"
    if len(fields) <= 1:
        return next_id

    items.append(
        EvidenceItem(
            evidence_id=f"E-{next_id:03d}",
            canonical_section=_infer_canonical_section(table.section_path, table.title),
            claim_summary=f"{table.title}中，{fields.get('覆盖项目', first_column)}合计数据为：{fields}",
            source_type="table_fact",
            source_file=table.source_file,
            page_number=table.page_number,
            table_id=table.table_id,
            table_title=table.title,
            section_path=table.section_path or ["未识别章节"],
            fields=fields,
            quality_status=QualityStatus.safe_to_use,
        )
    )
    next_id += 1

    total_ratio_text = fields.get("占比合计")
    total_ratio = _number_from_text(total_ratio_text or "")
    covered_items = fields.get("覆盖项目")
    if covered_items and total_ratio is not None and total_ratio >= 80:
        items.append(
            EvidenceItem(
                evidence_id=f"E-{next_id:03d}",
                canonical_section=_infer_canonical_section(table.section_path, table.title),
                claim_summary=(
                    f"{table.title}中，{covered_items}合计占比达到{total_ratio_text}，"
                    "超过八成"
                ),
                source_type="table_fact",
                source_file=table.source_file,
                page_number=table.page_number,
                table_id=table.table_id,
                table_title=table.title,
                section_path=table.section_path or ["未识别章节"],
                fields={
                    "覆盖项目": covered_items,
                    "占比合计": total_ratio_text,
                    "集中度判断": "超过八成",
                },
                quality_status=QualityStatus.safe_to_use,
            )
        )
        next_id += 1

    for numeric_column in numeric_columns:
        sorted_rows = sorted(
            table.rows,
            key=lambda row: _number_from_text(row[numeric_column])
            if numeric_column < len(row) and _number_from_text(row[numeric_column]) is not None
            else float("-inf"),
            reverse=True,
        )
        if len(sorted_rows) < 2:
            continue

        top_row = sorted_rows[0]
        second_row = sorted_rows[1]
        top_value = _number_from_text(top_row[numeric_column])
        second_value = _number_from_text(second_row[numeric_column])
        if top_value is None or second_value is None:
            continue

        raw_values = [
            row[numeric_column]
            for row in table.rows
            if numeric_column < len(row)
        ]
        unit = _unit_from_values(raw_values)
        gap_unit = "个百分点" if unit == "%" else unit
        gap = top_value - second_value
        metric_name = table.columns[numeric_column]
        fields = {
            "第一项": top_row[0],
            "第二项": second_row[0],
            "比较指标": metric_name,
            metric_name: top_row[numeric_column],
            "差额": f"{_format_number(gap)}{gap_unit}",
        }
        items.append(
            EvidenceItem(
                evidence_id=f"E-{next_id:03d}",
                canonical_section=_infer_canonical_section(table.section_path, table.title),
                claim_summary=(
                    f"{table.title}中，{top_row[0]}按{metric_name}"
                    f"高于{second_row[0]}，差额为{fields['差额']}"
                ),
                source_type="table_fact",
                source_file=table.source_file,
                page_number=table.page_number,
                table_id=table.table_id,
                table_title=table.title,
                section_path=table.section_path or ["未识别章节"],
                fields=fields,
                quality_status=QualityStatus.safe_to_use,
            )
        )
        next_id += 1

    return next_id


def build_evidence_packet(
    doc_id: str,
    source_file: str,
    blocks: list[Block],
    tables: list[TableObject],
) -> EvidencePacket:
    items: list[EvidenceItem] = []
    next_id = 1
    for block in blocks:
        section_path, evidence_text = _split_heading_and_body(block)
        evidence_block = block.model_copy(
            update={"text": evidence_text, "section_path": section_path},
            deep=True,
        )
        if _looks_like_directory(evidence_text) or _is_heading_only(evidence_text):
            continue
        if _is_excluded_section(section_path):
            continue
        if _is_html_table_block(evidence_text):
            for html_table in _html_tables_from_block(evidence_block, source_file):
                next_id = _append_table_row_items(items, next_id, html_table)
            continue
        if _score_text_block(evidence_block) < _MIN_TEXT_EVIDENCE_SCORE:
            continue
        items.append(
            EvidenceItem(
                evidence_id=f"E-{next_id:03d}",
                canonical_section=_infer_canonical_section(section_path, evidence_text),
                claim_summary=evidence_text.rstrip("。") + "。",
                source_type="text_quote",
                source_file=source_file,
                page_number=block.page_number,
                block_id=block.block_id,
                section_path=section_path or ["未识别章节"],
                quote=evidence_text,
                quality_status=QualityStatus.safe_to_use,
            )
        )
        next_id += 1
        if "研发、生产和销售" in evidence_text:
            items.append(
                EvidenceItem(
                    evidence_id=f"E-{next_id:03d}",
                    canonical_section="business_and_product",
                    claim_summary="公司业务链条覆盖研发、生产和销售环节。",
                    source_type="text_quote",
                    source_file=source_file,
                    page_number=block.page_number,
                    block_id=block.block_id,
                    section_path=section_path or ["未识别章节"],
                    quote=evidence_text,
                    quality_status=QualityStatus.safe_to_use,
                )
            )
            next_id += 1
    for table in tables:
        if table.quality_score >= 0.75 and table.rows:
            next_id = _append_table_row_items(items, next_id, table)
            next_id = _append_table_summary_items(items, next_id, table)
    return EvidencePacket(doc_id=doc_id, items=items)
