from __future__ import annotations

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
)
_SECTION_CANONICAL_PATTERNS = (
    ("business_and_product", ("业务与技术", "业务和技术", "主营业务", "主要产品", "产品或服务")),
    ("financials", ("财务会计信息", "管理层讨论与分析", "财务")),
    ("use_of_proceeds", ("募集资金运用", "募集资金用途")),
    ("risks", ("风险因素",)),
    ("about_company", ("发行人基本情况", "发行人概况", "公司设立")),
)
_EXCLUDED_SECTION_PATTERNS = (
    "释义",
    "附件",
    "发行人声明",
    "招股说明书",
)
_HTML_TABLE_PATTERN = re.compile(r"<table\b", re.IGNORECASE)
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
)


def _looks_like_directory(text: str) -> bool:
    compact = " ".join(text.split())
    return bool(_TOC_DOT_PATTERN.search(compact) or _TOC_MULTI_SECTION_PATTERN.search(compact))


def _is_heading_only(text: str) -> bool:
    return normalize_heading(text) is not None


def _is_fact_like_text(text: str) -> bool:
    return any(pattern in text for pattern in _FACT_TEXT_PATTERNS)


def _is_excluded_section(section_path: list[str]) -> bool:
    return any(
        excluded in section
        for section in section_path
        for excluded in _EXCLUDED_SECTION_PATTERNS
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


def build_evidence_packet(
    doc_id: str,
    source_file: str,
    blocks: list[Block],
    tables: list[TableObject],
) -> EvidencePacket:
    items: list[EvidenceItem] = []
    next_id = 1
    for block in blocks:
        if _looks_like_directory(block.text) or _is_heading_only(block.text):
            continue
        if _is_html_table_block(block.text) or _is_excluded_section(block.section_path):
            continue
        if _score_text_block(block) < _MIN_TEXT_EVIDENCE_SCORE:
            continue
        items.append(
            EvidenceItem(
                evidence_id=f"E-{next_id:03d}",
                canonical_section=_infer_canonical_section(block.section_path, block.text),
                claim_summary=block.text.rstrip("。") + "。",
                source_type="text_quote",
                source_file=source_file,
                page_number=block.page_number,
                block_id=block.block_id,
                section_path=block.section_path or ["未识别章节"],
                quote=block.text,
                quality_status=QualityStatus.safe_to_use,
            )
        )
        next_id += 1
    for table in tables:
        if table.quality_score >= 0.75 and table.rows:
            fields = {
                table.columns[index]: table.rows[0][index]
                for index in range(min(len(table.columns), len(table.rows[0])))
            }
            if not fields:
                continue
            items.append(
                EvidenceItem(
                    evidence_id=f"E-{next_id:03d}",
                    canonical_section=_infer_canonical_section(table.section_path, table.title),
                    claim_summary=f"{table.title}显示：{fields}",
                    source_type="table_fact",
                    source_file=source_file,
                    page_number=table.page_number,
                    table_id=table.table_id,
                    table_title=table.title,
                    section_path=table.section_path or ["未识别章节"],
                    fields=fields,
                    quality_status=QualityStatus.safe_to_use,
                )
            )
            next_id += 1
    return EvidencePacket(doc_id=doc_id, items=items)
