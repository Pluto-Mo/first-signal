from __future__ import annotations

import re

from ipo_evidence.models import (
    Citation,
    EvidencePacket,
    Manifest,
    ReaderBlock,
    ReaderBundle,
    ReaderCitation,
    ReaderCitationLocation,
    ReaderSection,
)


HEADING_RE = re.compile(r"^##\s+(.+)$")
SUBHEADING_RE = re.compile(r"^###\s+(.+)$")
CITATION_RE = re.compile(r"\[(C-\d{3})\]")


def _paragraphs(text: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", text.strip()) if chunk.strip()]


def _clean_body(text: str) -> str:
    without_citations = CITATION_RE.sub("", text)
    return " ".join(without_citations.split()).strip()


def _field_value(citation: Citation) -> str | None:
    if not citation.fields:
        return None
    return "；".join(f"{key}：{value}" for key, value in citation.fields.items())


def _excerpt(citation: Citation) -> str:
    if citation.quote:
        return citation.quote
    if citation.fields:
        return _field_value(citation) or citation.summary
    return citation.summary


def _label(citation: Citation) -> str:
    if citation.table_title:
        return citation.table_title
    if citation.section_path:
        return citation.section_path[-1]
    return citation.summary[:24]


def _reader_citations(citations: list[Citation], packet: EvidencePacket) -> list[ReaderCitation]:
    quality_lookup = {
        f"C-{index:03d}": item.quality_status for index, item in enumerate(packet.items, start=1)
    }
    reader_citations: list[ReaderCitation] = []
    for citation in citations:
        reader_citations.append(
            ReaderCitation(
                id=citation.citation_id,
                label=_label(citation),
                summary=citation.summary,
                quality=quality_lookup[citation.citation_id],
                excerpt=_excerpt(citation),
                location=ReaderCitationLocation(
                    source_file=citation.source_file,
                    page_number=citation.page_number,
                    block_id=citation.block_id,
                    section_path=citation.section_path,
                    table_id=citation.table_id,
                    table_title=citation.table_title,
                    field_value=_field_value(citation),
                ),
            )
        )
    return reader_citations


def _build_section(section_id: int, title: str, body: str) -> ReaderSection | None:
    blocks: list[ReaderBlock] = []
    pending_title: str | None = None
    block_index = 1
    for paragraph in _paragraphs(body):
        subheading = SUBHEADING_RE.match(paragraph)
        if subheading:
            pending_title = subheading.group(1).strip()
            continue
        cleaned = _clean_body(paragraph)
        if not cleaned:
            continue
        blocks.append(
            ReaderBlock(
                id=f"section-{section_id:03d}-block-{block_index:03d}",
                kind="lead" if block_index == 1 else "finding",
                title=pending_title,
                body=cleaned,
                citation_ids=CITATION_RE.findall(paragraph),
            )
        )
        pending_title = None
        block_index += 1
    if not blocks:
        return None
    return ReaderSection(id=f"section-{section_id:03d}", title=title, blocks=blocks)


def _parse_sections(report: str) -> tuple[str, list[ReaderSection]]:
    lines = report.splitlines()
    if not lines:
        return "", []

    report_title = lines[0].removeprefix("#").strip()
    sections: list[ReaderSection] = []
    current_title = "总览"
    current_lines: list[str] = []
    section_id = 1

    for line in lines[1:]:
        match = HEADING_RE.match(line.strip())
        if match:
            section = _build_section(section_id, current_title, "\n".join(current_lines))
            if section:
                sections.append(section)
                section_id += 1
            current_title = match.group(1).strip()
            current_lines = []
            continue
        current_lines.append(line)

    section = _build_section(section_id, current_title, "\n".join(current_lines))
    if section:
        sections.append(section)

    return report_title, sections


def build_reader_bundle(
    manifest: Manifest,
    report: str,
    citations: list[Citation],
    packet: EvidencePacket,
) -> ReaderBundle:
    report_title, sections = _parse_sections(report)
    return ReaderBundle(
        doc_id=manifest.doc_id,
        company_name=manifest.company_name,
        source_file=manifest.source_file,
        report_title=report_title,
        quality_status=manifest.quality_status,
        parse_status=manifest.parse_status,
        report_status=manifest.report_status,
        sections=sections,
        citations=_reader_citations(citations, packet),
    )
