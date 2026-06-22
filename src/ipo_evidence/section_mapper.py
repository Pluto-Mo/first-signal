from __future__ import annotations

import re

from ipo_evidence.models import AstNode, Block


CANONICAL_RULES = {
    "about_company": ("关于公司", ["发行人基本情况", "发行人概况"]),
    "business_and_product": ("业务与产品", ["业务和技术", "主营业务"]),
    "financials": ("财务与经营数据", ["财务会计信息", "管理层讨论与分析"]),
    "use_of_proceeds": ("募集资金用途", ["募集资金运用", "募集资金用途"]),
    "risks": ("风险因素", ["风险因素"]),
}


def normalize_heading(text: str) -> str | None:
    stripped = text.strip().lstrip("#").strip()
    match = re.match(r"第[一二三四五六七八九十]+节\s+(.+)", stripped)
    if match:
        return match.group(1).strip()
    return None


def build_source_ast(blocks: list[Block]) -> list[AstNode]:
    nodes: list[AstNode] = []
    current: AstNode | None = None
    for block in blocks:
        heading = normalize_heading(block.text)
        if heading:
            current = AstNode(
                title=heading,
                level=1,
                section_path=[heading],
                block_ids=[block.block_id],
            )
            nodes.append(current)
        elif current is not None:
            current.block_ids.append(block.block_id)
    return nodes


def map_canonical_sections(source_ast: list[AstNode]) -> dict:
    canonical: dict[str, dict] = {}
    for key, (title, patterns) in CANONICAL_RULES.items():
        matched = [
            node.title
            for node in source_ast
            if any(pattern in node.title for pattern in patterns)
        ]
        if matched:
            canonical[key] = {"title": title, "source_sections": matched}
    return canonical
