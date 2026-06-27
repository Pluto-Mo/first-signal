import "@testing-library/jest-dom";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";
import App from "../App";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("reader app", () => {
  test("renders a continuous article and opens citations in a drawer", async () => {
    const user = userEvent.setup();
    const docsIndex = [
      {
        doc_id: "doc_test",
        company_name: "测试股份有限公司",
        source_file: "测试股份有限公司招股说明书.pdf",
        quality_status: "safe_to_use",
        parse_status: "parsed",
        report_status: "reported",
        tags: [],
        report_path: "report.md",
        citation_path: "citation.json",
        reader_bundle_path: "doc_test/reader_bundle.json"
      }
    ];
    const readerBundle = {
      doc_id: "doc_test",
      company_name: "测试股份有限公司",
      source_file: "测试股份有限公司招股说明书.pdf",
      report_title: "测试股份有限公司招股书长篇阅读",
      quality_status: "safe_to_use",
      parse_status: "parsed",
      report_status: "reported",
      sections: [
        {
          id: "section-001",
          title: "总览",
          blocks: [
            {
              id: "section-001-block-001",
              kind: "lead",
              body: "导语判断，适合作为总览入口。",
              citation_ids: ["C-001"]
            }
          ]
        },
        {
          id: "section-002",
          title: "一、业务概况",
          blocks: [
            {
              id: "section-002-block-001",
              kind: "finding",
              body: "公司主营业务集中在智能控制器。",
              citation_ids: ["C-002"]
            }
          ]
        }
      ],
      citations: [
        {
          id: "C-001",
          label: "发行人基本情况",
          summary: "导语判断，适合作为总览入口。",
          quality: "safe_to_use",
          excerpt: "导语判断，适合作为总览入口。",
          location: {
            source_file: "测试股份有限公司招股说明书.pdf",
            page_number: 2,
            block_id: "B-000001",
            section_path: ["发行人基本情况"]
          }
        },
        {
          id: "C-002",
          label: "主营业务",
          summary: "公司主营业务集中在智能控制器。",
          quality: "manual_review",
          excerpt: "公司主营业务集中在智能控制器。",
          location: {
            source_file: "测试股份有限公司招股说明书.pdf",
            page_number: 3,
            block_id: "B-000002",
            section_path: ["业务和技术", "主营业务"],
            table_id: null,
            table_title: null,
            field_value: null
          }
        }
      ]
    };
    const responses: Record<string, unknown> = {
      "/index.json": docsIndex,
      "/doc_test/reader_bundle.json": readerBundle
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const key = typeof input === "string" ? input : String(input);
        const payload = responses[key];

        if (!payload) {
          return {
            ok: false,
            status: 404,
            json: async () => ({})
          } as Response;
        }

        return {
          ok: true,
          status: 200,
          json: async () => payload
        } as Response;
      })
    );

    render(<App />);

    expect(await screen.findByText("测试股份有限公司")).toBeInTheDocument();
    expect(
      screen.getAllByText("导语判断，适合作为总览入口。").length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("公司主营业务集中在智能控制器。").length
    ).toBeGreaterThan(0);
    expect(screen.queryByRole("tab", { name: "一、业务概况" })).not.toBeInTheDocument();
    expect(screen.queryByText("引用 C-001")).not.toBeInTheDocument();

    const citationChip = screen.getByRole("button", { name: /查看引用 C-002/ });
    expect(citationChip).toHaveClass("citation-chip");

    await user.click(citationChip);

    const drawer = screen.getByRole("complementary", { name: "引用抽屉" });
    expect(within(drawer).getByText("引用 C-002")).toBeInTheDocument();
    expect(within(drawer).getByText("招股说明书 第 3 页")).toBeInTheDocument();
    expect(within(drawer).getByText("业务和技术 / 主营业务")).toBeInTheDocument();
    expect(within(drawer).queryByText("null")).not.toBeInTheDocument();

    await user.click(within(drawer).getByRole("button", { name: "关闭引用" }));

    expect(screen.queryByRole("complementary", { name: "引用抽屉" })).not.toBeInTheDocument();
  });
});
