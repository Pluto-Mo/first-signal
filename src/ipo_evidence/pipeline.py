from __future__ import annotations

from pathlib import Path

from ipo_evidence.analysis_log import build_analysis_log
from ipo_evidence.citation_layer import build_citations
from ipo_evidence.config import load_yaml
from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.ingest import company_name_from_filename, doc_id_for_file
from ipo_evidence.io import ensure_dir, read_json, write_json, write_jsonl, write_text
from ipo_evidence.models import EvidencePacket, Manifest, QualityStatus
from ipo_evidence.parser import create_parser
from ipo_evidence.quality_gate import apply_quality_gate
from ipo_evidence.reader_bundle import build_reader_bundle
from ipo_evidence.report_inputs import build_report_inputs
from ipo_evidence.report_generator import generate_report
from ipo_evidence.section_generator import generate_section_drafts
from ipo_evidence.section_mapper import assign_section_paths, build_source_ast, map_canonical_sections
from ipo_evidence.table_extractor import extract_tables
from ipo_evidence.web_index import build_web_index, refresh_docs_index


def _read_report_inputs(package_dir: Path) -> dict | None:
    report_inputs_path = package_dir / "report_inputs.json"
    if not report_inputs_path.exists():
        return None
    report_inputs = read_json(report_inputs_path)
    if not isinstance(report_inputs, dict):
        raise ValueError(f"report_inputs must be a JSON object: {report_inputs_path}")
    return report_inputs


def _evidence_policies(report_inputs: dict | None) -> dict[str, dict]:
    if not report_inputs:
        return {}
    groups = report_inputs.get("section_groups", [])
    if not isinstance(groups, list):
        return {}
    policies: dict[str, dict] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        section_key = group.get("section_key")
        policy = group.get("evidence_policy")
        if isinstance(section_key, str) and isinstance(policy, dict):
            policies[section_key] = policy
    return policies


def _write_report_artifacts(
    package_dir: Path,
    manifest: Manifest,
    packet: EvidencePacket,
    report_inputs: dict | None = None,
) -> None:
    report = generate_report(manifest.company_name, packet, report_inputs)
    citations = build_citations(packet)
    section_drafts = generate_section_drafts(packet, report_inputs)
    quality_decisions = apply_quality_gate(section_drafts, _evidence_policies(report_inputs))
    analysis_log = build_analysis_log(packet.doc_id, quality_decisions)
    reader_bundle = build_reader_bundle(manifest, report, citations, packet)
    web_index = build_web_index(manifest)

    write_text(package_dir / "report.md", report)
    write_json(
        package_dir / "citation.json",
        [citation.model_dump(mode="json") for citation in citations],
    )
    write_json(package_dir / "analysis_log.json", analysis_log)
    write_json(package_dir / "reader_bundle.json", reader_bundle)
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

    parser_config = load_yaml("configs/parser.yaml")
    parser = create_parser(parser_config, fixture_path=fixture_path)
    parsed = parser.parse(pdf_path)
    company_name = parsed.parse_report.get("company_name") or company_name
    manifest.company_name = company_name
    assigned_blocks = assign_section_paths(parsed.blocks)
    source_ast = build_source_ast(assigned_blocks)
    canonical_ast = map_canonical_sections(source_ast)
    tables = extract_tables(parsed.raw_tables, source_file, ["业务和技术"])
    packet = build_evidence_packet(doc_id, source_file, assigned_blocks, tables)
    report_inputs = build_report_inputs(doc_id, company_name, packet)
    write_json(package_dir / "manifest.json", manifest)
    write_text(package_dir / "document.md", parsed.markdown)
    write_jsonl(package_dir / "blocks.jsonl", assigned_blocks)
    write_json(
        package_dir / "source_ast.json",
        [node.model_dump(mode="json") for node in source_ast],
    )
    write_json(package_dir / "canonical_ast.json", canonical_ast)
    tables_dir = ensure_dir(package_dir / "tables")
    for table in tables:
        write_json(tables_dir / f"{table.table_id}.json", table)
    write_json(package_dir / "evidence_packet.json", packet)
    write_json(package_dir / "report_inputs.json", report_inputs)
    write_json(package_dir / "parse_report.json", parsed.parse_report)
    if parsed.raw_artifacts:
        write_json(package_dir / "parser_raw.json", parsed.raw_artifacts)
    manifest.report_status = "reported"
    _write_report_artifacts(package_dir, manifest, packet, report_inputs)
    write_json(package_dir / "manifest.json", manifest)
    write_json(package_dir / "web_index.json", build_web_index(manifest))
    refresh_docs_index(docs_dir)
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
    report_inputs = _read_report_inputs(package_dir)
    if report_inputs and report_inputs.get("doc_id") != doc_id:
        raise ValueError(
            f"report inputs doc_id mismatch: expected {doc_id}, got {report_inputs.get('doc_id')}"
        )

    manifest.report_status = "reported"
    write_json(manifest_path, manifest)
    _write_report_artifacts(package_dir, manifest, packet, report_inputs)
    refresh_docs_index(docs_dir)
