import docsIndex from "../../../data/docs/index.json";
import type { Citation, DocumentRecord, ReportSection } from "./types";

type DocsIndexItem = {
  doc_id: string;
  company_name: string;
  source_file: string;
  quality_status: "safe_to_use" | "manual_review" | "do_not_use";
  parse_status: string;
  report_status: string;
};

type RawCitation = {
  citation_id: string;
  type: "text_quote" | "table_fact";
  source_file: string;
  page_number: number;
  block_id: string | null;
  table_id?: string | null;
  section_path: string[];
  quote: string | null;
  table_title?: string | null;
  fields: Record<string, string>;
  summary: string;
};

type RawManifest = {
  doc_id: string;
  company_name: string;
  source_file: string;
  quality_status: "safe_to_use" | "manual_review" | "do_not_use";
};

const manifestModules = import.meta.glob("../../../data/docs/*/manifest.json", {
  eager: true,
  import: "default"
}) as Record<string, RawManifest>;

const citationModules = import.meta.glob("../../../data/docs/*/citation.json", {
  eager: true,
  import: "default"
}) as Record<string, RawCitation[]>;

const reportModules = import.meta.glob("../../../data/docs/*/report.md", {
  eager: true,
  query: "?raw",
  import: "default"
}) as Record<string, string>;

const sourceModules = import.meta.glob("../../../data/docs/*/document.md", {
  eager: true,
  query: "?raw",
  import: "default"
}) as Record<string, string>;

const fallbackDocuments: DocumentRecord[] = [
  {
    id: "fallback-doc",
    companyName: "测试股份有限公司",
    exchange: "A股招股说明书",
    reportTitle: "测试股份有限公司招股书解读",
    reportDate: "示例数据",
    quality: "safe_to_use",
    sourceMarkdown: "# 原文\n\n暂无真实文档包。",
    citations: [
      {
        id: "C-001",
        label: "示例引用",
        summary: "当前正在展示前端回退示例数据。",
        quality: "manual_review",
        excerpt: "暂无真实文档包。",
        location: {
          source_file: "sample.pdf",
          page_number: 1,
          block_id: "B-000001",
          section_path: "示例章节"
        }
      }
    ],
    sections: [
      {
        id: "section-1",
        title: "处理结论",
        blocks: [
          {
            id: "block-1",
            kind: "note",
            title: "处理结论",
            body: "当前正在展示前端回退示例数据。",
            citationIds: ["C-001"]
          }
        ]
      }
    ]
  }
];

function sectionTitleFromHeading(heading: string) {
  return heading.replace(/^\d+\.\s*/, "").trim();
}

function normalizeFieldValue(fields: Record<string, string>) {
  return Object.values(fields).join(" / ");
}

function mapCitation(raw: RawCitation): Citation {
  return {
    id: raw.citation_id,
    label: raw.table_title ?? raw.summary.slice(0, 20),
    summary: raw.summary,
    quality: "safe_to_use",
    excerpt: raw.quote ?? raw.table_title ?? raw.summary,
    location: {
      source_file: raw.source_file,
      page_number: raw.page_number,
      block_id: raw.block_id ?? `table:${raw.table_id ?? "unknown"}`,
      section_path: raw.section_path.join(" / "),
      table_id: raw.table_id ?? undefined,
      table_title: raw.table_title ?? undefined,
      field_value: Object.keys(raw.fields).length > 0 ? normalizeFieldValue(raw.fields) : undefined
    }
  };
}

function splitReportIntoSections(markdown: string, citations: Citation[]): ReportSection[] {
  const lines = markdown.split(/\r?\n/);
  const sections: ReportSection[] = [];
  let current: ReportSection | null = null;
  let blockNumber = 1;

  const citationIds = citations.map((citation) => citation.id);

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line || line.startsWith("# ")) {
      continue;
    }

    if (line.startsWith("## ")) {
      if (current) {
        sections.push(current);
      }
      const title = sectionTitleFromHeading(line.slice(3));
      current = {
        id: `section-${sections.length + 1}`,
        title,
        blocks: []
      };
      continue;
    }

    if (!current) {
      continue;
    }

    const matchedCitationIds = Array.from(
      new Set(line.match(/\[C-\d{3}\]/g)?.map((token) => token.slice(1, -1)) ?? [])
    );
    const cleanedBody = line
      .replace(/^- /, "")
      .replace(/\[C-\d{3}\]/g, "")
      .trim();

    const fallbackCitationIds =
      matchedCitationIds.length > 0 ? matchedCitationIds : current.blocks.length === 0 ? [] : citationIds;

    current.blocks.push({
      id: `block-${blockNumber}`,
      kind: current.blocks.length === 0 ? "finding" : "note",
      title: current.blocks.length === 0 ? current.title : undefined,
      body: cleanedBody,
      citationIds: fallbackCitationIds
    });
    blockNumber += 1;
  }

  if (current) {
    sections.push(current);
  }

  return sections.length > 0 ? sections : fallbackDocuments[0].sections;
}

function buildDocumentRecord(
  indexItem: DocsIndexItem,
  manifest: RawManifest,
  rawCitations: RawCitation[],
  report: string,
  source: string
): DocumentRecord {
  const citations = rawCitations.map(mapCitation);

  return {
    id: indexItem.doc_id,
    companyName: manifest.company_name,
    exchange: "A股招股说明书",
    reportTitle: `${manifest.company_name}招股书解读`,
    reportDate: "本地文档包",
    quality: manifest.quality_status,
    sourceMarkdown: source,
    citations,
    sections: splitReportIntoSections(report, citations)
  };
}

function findModuleValue<T>(modules: Record<string, T>, docId: string): T | null {
  const key = Object.keys(modules).find((modulePath) => modulePath.includes(`/${docId}/`));
  return key ? modules[key] : null;
}

const realDocuments = Array.isArray(docsIndex)
  ? docsIndex
      .map((item) => {
        const indexItem = item as DocsIndexItem;
        const manifest = findModuleValue(manifestModules, indexItem.doc_id);
        const rawCitations = findModuleValue(citationModules, indexItem.doc_id);
        const report = findModuleValue(reportModules, indexItem.doc_id);
        const source = findModuleValue(sourceModules, indexItem.doc_id);

        if (!manifest || !rawCitations || !report || !source) {
          return null;
        }

        return buildDocumentRecord(indexItem, manifest, rawCitations, report, source);
      })
      .filter((document): document is DocumentRecord => document !== null)
  : [];

export const documents: DocumentRecord[] =
  realDocuments.length > 0 ? realDocuments : fallbackDocuments;

export function getDocumentById(documentId: string): DocumentRecord {
  const match = documents.find((document) => document.id === documentId);
  return match ?? documents[0];
}
