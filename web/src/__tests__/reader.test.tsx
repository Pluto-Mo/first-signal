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
    const createdAt = new Date().getTime();
    const docsIndex = [
      {
        doc_id: "doc_test",
        company_name: "测试股份有限公司",
        source_file: "测试股份有限公司招股说明书.pdf",
        industry: "智能制造",
        created_at: createdAt,
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

    expect(
      await screen.findByRole("heading", { name: "IPO 招股书研报" })
    ).toBeInTheDocument();
    expect(screen.queryByText("A股招股书证据阅读台")).not.toBeInTheDocument();
    expect(
      screen.queryByText("正文优先阅读，引用与来源定位放在右侧，适合边读边核。")
    ).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "按时间" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("button", { name: "最近三天，1 份文档" })).toBeInTheDocument();
    expect(await screen.findByText("测试股份有限公司")).toBeInTheDocument();
    expect(
      (await screen.findAllByText("导语判断，适合作为总览入口。")).length
    ).toBeGreaterThan(0);
    expect(
      (await screen.findAllByText("公司主营业务集中在智能控制器。")).length
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: "测试股份有限公司", level: 2 })
    ).toBeInTheDocument();
    expect(screen.queryByText("测试股份有限公司招股书长篇阅读")).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "一、业务概况" })).not.toBeInTheDocument();
    expect(screen.queryByText("引用 C-001")).not.toBeInTheDocument();

    const citationChip = screen.getByRole("button", { name: /查看引用 C-002/ });
    expect(citationChip).toHaveClass("citation-chip");

    await user.click(screen.getByRole("tab", { name: "按行业" }));
    expect(screen.getByRole("button", { name: "智能制造，1 份文档" })).toBeInTheDocument();

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
