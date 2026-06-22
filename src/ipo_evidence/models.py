from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class QualityStatus(StrEnum):
    safe_to_use = "safe_to_use"
    manual_review = "manual_review"
    do_not_use = "do_not_use"


class Manifest(BaseModel):
    doc_id: str
    company_name: str
    source_file: str
    source_url: str | None = None
    market: Literal["a_share"] = "a_share"
    document_type: str = "招股说明书"
    input_type: Literal["local_pdf"] = "local_pdf"
    parse_status: str = "discovered"
    report_status: str = "not_started"
    quality_status: QualityStatus = QualityStatus.manual_review
    tags: list[str] = Field(default_factory=list)


class Block(BaseModel):
    block_id: str
    page_number: int
    text: str
    section_path: list[str] = Field(default_factory=list)


class AstNode(BaseModel):
    title: str
    level: int
    section_path: list[str]
    block_ids: list[str] = Field(default_factory=list)
    children: list["AstNode"] = Field(default_factory=list)


class TableObject(BaseModel):
    table_id: str
    title: str
    source_file: str
    page_number: int
    section_path: list[str]
    columns: list[str]
    rows: list[list[str]]
    notes: list[str] = Field(default_factory=list)
    quality_score: float = 0.0


class EvidenceItem(BaseModel):
    evidence_id: str
    canonical_section: str
    claim_summary: str
    source_type: Literal["text_quote", "table_fact"]
    source_file: str
    page_number: int
    block_id: str | None = None
    table_id: str | None = None
    section_path: list[str]
    quote: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    quality_status: QualityStatus = QualityStatus.manual_review


class EvidencePacket(BaseModel):
    doc_id: str
    items: list[EvidenceItem]


class Citation(BaseModel):
    citation_id: str
    type: Literal["text_quote", "table_fact"]
    source_file: str
    source_url: str | None = None
    page_number: int
    block_id: str | None = None
    table_id: str | None = None
    section_path: list[str]
    quote: str | None = None
    table_title: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    summary: str


class WebIndex(BaseModel):
    doc_id: str
    company_name: str
    source_file: str
    quality_status: QualityStatus
    parse_status: str
    report_status: str
    tags: list[str] = Field(default_factory=list)
    report_path: str = "report.md"
    citation_path: str = "citation.json"


JsonDict = dict[str, Any]
