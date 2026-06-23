from __future__ import annotations

from pathlib import Path

from ipo_evidence.citation_layer import build_citations
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.ingest import company_name_from_filename, doc_id_for_file
from ipo_evidence.io import ensure_dir, read_json, write_json, write_jsonl, write_text
from ipo_evidence.models import EvidencePacket, Manifest, QualityStatus
from ipo_evidence.parser.api_stub import ApiStubParser
from ipo_evidence.report_generator import generate_report
from ipo_evidence.section_mapper import build_source_ast, map_canonical_sections
from ipo_evidence.table_extractor import extract_tables
from ipo_evidence.web_index import build_web_index


def _write_report_artifacts(package_dir: Path, manifest: Manifest, packet: EvidencePacket) -> None:
    report = generate_report(manifest.company_name, packet)
    citations = build_citations(packet)
    web_index = build_web_index(manifest)

    write_text(package_dir / "report.md", report)
    write_json(
        package_dir / "citation.json",
        [citation.model_dump(mode="json") for citation in citations],
    )
    write_json(package_dir / "web_index.json", web_index)


def run_one(pdf_path: Path, docs_dir: Path, fixture_path: Path) -> str:
    doc_id = doc_id_for_file(pdf_path)
    package_dir = ensure_dir(docs_dir / doc_id)
    source_file = pdf_path.name
    company_name = company_name_from_filename(pdf_path)
    manifest = Manifest(
        doc_id=doc_id,
        company_name=company_name,
        source_file=source_file,
        parse_status="parsed",
        report_status="not_started",
        quality_status=QualityStatus.safe_to_use,
    )

    parser = ApiStubParser(fixture_path=fixture_path)
    parsed = parser.parse(pdf_path)
    source_ast = build_source_ast(parsed.blocks)
    canonical_ast = map_canonical_sections(source_ast)
    tables = extract_tables(parsed.raw_tables, source_file, ["业务和技术"])
    packet = build_evidence_packet(doc_id, source_file, parsed.blocks, tables)
    write_json(package_dir / "manifest.json", manifest)
    write_text(package_dir / "document.md", parsed.markdown)
    write_jsonl(package_dir / "blocks.jsonl", parsed.blocks)
    write_json(
        package_dir / "source_ast.json",
        [node.model_dump(mode="json") for node in source_ast],
    )
    write_json(package_dir / "canonical_ast.json", canonical_ast)
    tables_dir = ensure_dir(package_dir / "tables")
    for table in tables:
        write_json(tables_dir / f"{table.table_id}.json", table)
    write_json(package_dir / "evidence_packet.json", packet)
    write_json(package_dir / "parse_report.json", parsed.parse_report)
    _write_report_artifacts(package_dir, manifest, packet)
    manifest.report_status = "reported"
    write_json(package_dir / "manifest.json", manifest)
    write_json(package_dir / "web_index.json", build_web_index(manifest))
    return doc_id


def regenerate_report(doc_id: str, docs_dir: Path) -> None:
    package_dir = docs_dir / doc_id
    if not package_dir.exists() or not package_dir.is_dir():
        raise FileNotFoundError(f"document package not found for doc_id={doc_id}")

    manifest_path = package_dir / "manifest.json"
    packet_path = package_dir / "evidence_packet.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing required artifact: {manifest_path}")
    if not packet_path.exists():
        raise FileNotFoundError(f"missing required artifact: {packet_path}")

    manifest = Manifest.model_validate(read_json(manifest_path))
    if manifest.doc_id != doc_id:
        raise ValueError(f"manifest doc_id mismatch: expected {doc_id}, got {manifest.doc_id}")

    packet = EvidencePacket.model_validate(read_json(packet_path))
    if packet.doc_id != doc_id:
        raise ValueError(
            f"evidence packet doc_id mismatch: expected {doc_id}, got {packet.doc_id}"
        )

    manifest.report_status = "reported"
    write_json(manifest_path, manifest)
    _write_report_artifacts(package_dir, manifest, packet)
