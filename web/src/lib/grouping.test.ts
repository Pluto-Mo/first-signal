import { describe, expect, test } from "vitest";
import { groupByIndustry, groupByTime } from "./grouping";
import type { DocsIndexItem } from "./types";

function buildDocument(
  overrides: Partial<DocsIndexItem> & Pick<DocsIndexItem, "doc_id" | "company_name">
): DocsIndexItem {
  return {
    source_file: `${overrides.company_name}招股说明书.pdf`,
    quality_status: "safe_to_use",
    parse_status: "parsed",
    report_status: "reported",
    tags: [],
    report_path: "report.md",
    citation_path: "citation.json",
    reader_bundle_path: `${overrides.doc_id}/reader_bundle.json`,
    ...overrides
  };
}

describe("document grouping", () => {
  test("groups documents by recent time ranges", () => {
    const now = new Date("2026-07-02T12:00:00+08:00").getTime();
    const documents = [
      buildDocument({
        doc_id: "doc_recent",
        company_name: "思必驰科技股份有限公司",
        created_at: now - 24 * 60 * 60 * 1000
      }),
      buildDocument({
        doc_id: "doc_week",
        company_name: "永励精密股份有限公司",
        created_at: now - 5 * 24 * 60 * 60 * 1000
      }),
      buildDocument({
        doc_id: "doc_old",
        company_name: "康美特科技股份有限公司",
        created_at: now - 10 * 24 * 60 * 60 * 1000
      })
    ];

    const groups = groupByTime(documents, now);

    expect(groups.map((group) => group.label)).toEqual(["最近三天", "本周", "更早"]);
    expect(groups[0].documents.map((document) => document.doc_id)).toEqual(["doc_recent"]);
    expect(groups[1].documents.map((document) => document.doc_id)).toEqual(["doc_week"]);
    expect(groups[2].documents.map((document) => document.doc_id)).toEqual(["doc_old"]);
  });

  test("groups documents by explicit or inferred industry", () => {
    const documents = [
      buildDocument({
        doc_id: "doc_ai",
        company_name: "思必驰科技股份有限公司",
        created_at: 10
      }),
      buildDocument({
        doc_id: "doc_energy",
        company_name: "华润新能源控股有限公司",
        industry: "新能源",
        created_at: 20
      }),
      buildDocument({
        doc_id: "doc_unknown",
        company_name: "测试股份有限公司",
        created_at: 5
      })
    ];

    const groups = groupByIndustry(documents);

    expect(groups.find((group) => group.label === "人工智能")?.documents[0].doc_id).toBe(
      "doc_ai"
    );
    expect(groups.find((group) => group.label === "新能源")?.documents[0].doc_id).toBe(
      "doc_energy"
    );
    expect(groups.find((group) => group.label === "未分类")?.documents[0].doc_id).toBe(
      "doc_unknown"
    );
  });

  test("uses official published_at before generated created_at", () => {
    const now = new Date("2026-07-02T12:00:00+08:00").getTime();
    const groups = groupByTime(
      [
        buildDocument({
          doc_id: "doc_official",
          company_name: "永励精密股份有限公司",
          published_at: "2026-06-22",
          created_at: now
        })
      ],
      now
    );

    expect(groups.map((group) => group.label)).toEqual(["更早"]);
  });
});
