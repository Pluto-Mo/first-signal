from __future__ import annotations

from ipo_evidence.models import Citation, EvidencePacket


def build_citations(packet: EvidencePacket) -> list[Citation]:
    citations: list[Citation] = []
    for index, item in enumerate(packet.items, start=1):
        citation_id = f"C-{index:03d}"
        citations.append(
            Citation(
                citation_id=citation_id,
                type=item.source_type,
                source_file=item.source_file,
                source_url=None,
                page_number=item.page_number,
                block_id=item.block_id,
                table_id=item.table_id,
                table_title=item.table_title,
                section_path=item.section_path,
                quote=item.quote,
                fields=item.fields,
                summary=item.claim_summary,
            )
        )
    return citations
