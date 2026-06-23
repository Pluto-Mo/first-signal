from __future__ import annotations

import re

from ipo_evidence.models import AstNode, Block


CANONICAL_RULES = {
    "about_company": ("关于公司", ["发行人基本情况", "发行人概况"]),
    "business_and_product": ("业务与产品", ["业务和技术", "业务与技术", "主营业务", "主要产品", "产品或服务"]),
    "financials": ("财务与经营数据", ["财务会计信息", "管理层讨论与分析"]),
    "use_of_proceeds": ("募集资金用途", ["募集资金运用", "募集资金用途"]),
    "risks": ("风险因素", ["风险因素"]),
}

_HEADING_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"^第[一二三四五六七八九十百零]+节\s*(.+)$"), 1),
    (re.compile(r"^[一二三四五六七八九十百零]+、\s*(.+)$"), 2),
    (re.compile(r"^（[一二三四五六七八九十百零]+）\s*(.+)$"), 3),
    (re.compile(r"^\(([一二三四五六七八九十百零]+)\)\s*(.+)$"), 3),
    (re.compile(r"^(\d+(?:\.\d+)*)(?:[、.．])?\s*(.+)$"), 0),
]


def _strip_markdown_heading(text: str) -> tuple[int, str]:
    stripped = text.strip()
    match = re.match(r"^(#{1,6})\s*(.+)$", stripped)
    if not match:
        return 0, stripped
    return len(match.group(1)), match.group(2).strip()


def _numeric_level(numbering: str) -> int:
    return numbering.count(".") + 1


def normalize_heading(text: str) -> tuple[int, str] | None:
    markdown_level, body = _strip_markdown_heading(text)
    if not body:
        return None

    for pattern, fixed_level in _HEADING_PATTERNS:
        match = pattern.match(body)
        if not match:
            continue
        if fixed_level:
            title = match.group(match.lastindex or 1).strip()
            if title:
                return fixed_level, title
            return None

        numbering = match.group(1).strip()
        title = match.group(2).strip()
        level = _numeric_level(numbering)
        if markdown_level:
            level = max(level, markdown_level)
        if title:
            return level, title
        return None

    if markdown_level and body:
        return markdown_level, body
    return None


def assign_section_paths(blocks: list[Block]) -> list[Block]:
    assigned: list[Block] = []
    current_path: list[str] = []
    for block in blocks:
        heading = normalize_heading(block.text)
        updated = block.model_copy(deep=True)
        if heading:
            level, title = heading
            while len(current_path) >= level:
                current_path.pop()
            current_path.append(title)
            updated.section_path = current_path.copy()
        elif current_path:
            updated.section_path = current_path.copy()
        assigned.append(updated)
    return assigned


def build_source_ast(blocks: list[Block]) -> list[AstNode]:
    assigned_blocks = assign_section_paths(blocks)
    nodes: list[AstNode] = []
    node_stack: list[AstNode] = []

    for block in assigned_blocks:
        heading = normalize_heading(block.text)
        if heading:
            level, title = heading
            node = AstNode(
                title=title,
                level=level,
                section_path=block.section_path,
                block_ids=[block.block_id],
            )
            while node_stack and node_stack[-1].level >= level:
                node_stack.pop()
            if node_stack:
                node_stack[-1].children.append(node)
            nodes.append(node)
            node_stack.append(node)
            continue

        if node_stack:
            node_stack[-1].block_ids.append(block.block_id)

    return nodes


def map_canonical_sections(source_ast: list[AstNode]) -> dict:
    canonical: dict[str, dict] = {}
    for key, (title, patterns) in CANONICAL_RULES.items():
        matched = [
            node.title
            for node in source_ast
            if any(pattern in part for part in node.section_path for pattern in patterns)
        ]
        deduped = list(dict.fromkeys(matched))
        if deduped:
            canonical[key] = {"title": title, "source_sections": deduped}
    return canonical
