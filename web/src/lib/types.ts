export type QualityStatus = "safe_to_use" | "manual_review" | "do_not_use";

export interface CitationLocation {
  source_file: string;
  page_number: number;
  block_id: string;
  section_path: string;
  table_id?: string;
  table_title?: string;
  field_value?: string;
}

export interface Citation {
  id: string;
  label: string;
  summary: string;
  quality: QualityStatus;
  excerpt: string;
  location: CitationLocation;
}

export interface ReportBlock {
  id: string;
  kind: "lead" | "finding" | "note";
  title?: string;
  body: string;
  citationIds: string[];
}

export interface ReportSection {
  id: string;
  title: string;
  blocks: ReportBlock[];
}

export interface DocumentRecord {
  id: string;
  companyName: string;
  exchange: string;
  reportTitle: string;
  reportDate: string;
  quality: QualityStatus;
  sections: ReportSection[];
  citations: Citation[];
  sourceMarkdown: string;
}
