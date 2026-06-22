from __future__ import annotations

from ipo_evidence.models import Block, EvidenceItem, EvidencePacket, QualityStatus, TableObject


def build_evidence_packet(
    doc_id: str,
    source_file: str,
    blocks: list[Block],
    tables: list[TableObject],
) -> EvidencePacket:
    items: list[EvidenceItem] = []
    next_id = 1
    for block in blocks:
        if "公司主要从事" in block.text or "主要产品" in block.text:
            items.append(
                EvidenceItem(
                    evidence_id=f"E-{next_id:03d}",
                    canonical_section="about_company",
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
            items.append(
                EvidenceItem(
                    evidence_id=f"E-{next_id:03d}",
                    canonical_section="business_and_product",
                    claim_summary=f"{table.title}显示：{fields}",
                    source_type="table_fact",
                    source_file=source_file,
                    page_number=table.page_number,
                    table_id=table.table_id,
                    table_title=table.title,
                    section_path=table.section_path,
                    fields=fields,
                    quality_status=QualityStatus.safe_to_use,
                )
            )
            next_id += 1
    return EvidencePacket(doc_id=doc_id, items=items)
