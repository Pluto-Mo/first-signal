import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";

vi.mock("../lib/data", () => ({
  documents: [
    {
      id: "doc_test",
      companyName: "测试股份有限公司",
      exchange: "A股招股说明书",
      reportTitle: "测试股份有限公司招股书解读",
      reportDate: "本地文档包",
      quality: "safe_to_use",
      sourceMarkdown: "# 原文",
      citations: [
        {
          id: "C-001",
          label: "产品收入结构表",
          summary: "产品收入结构表显示：智能控制器收入 12000 万元，占比 45.2%。",
          quality: "safe_to_use",
          excerpt: "产品收入结构表",
          location: {
            source_file: "测试股份有限公司招股说明书.pdf",
            page_number: 3,
            block_id: "table:T-001",
            section_path: "业务和技术",
            table_id: "T-001",
            table_title: "产品收入结构表",
            field_value: "智能控制器 / 12000万元 / 45.2%"
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
              kind: "finding",
              title: "处理结论",
              body: "当前报告由本地证据包生成，适合进行第一轮人工复核。",
              citationIds: []
            }
          ]
        },
        {
          id: "section-2",
          title: "关于公司",
          blocks: [
            {
              id: "block-2",
              kind: "finding",
              title: "关于公司",
              body: "产品收入结构表显示：智能控制器收入 12000 万元，占比 45.2%。",
              citationIds: ["C-001"]
            }
          ]
        }
      ]
    }
  ],
  getDocumentById: (documentId: string) => ({
    id: "doc_test",
    companyName: "测试股份有限公司",
    exchange: "A股招股说明书",
    reportTitle: "测试股份有限公司招股书解读",
    reportDate: "本地文档包",
    quality: "safe_to_use",
    sourceMarkdown: "# 原文",
    citations: [
      {
        id: "C-001",
        label: "产品收入结构表",
        summary: "产品收入结构表显示：智能控制器收入 12000 万元，占比 45.2%。",
        quality: "safe_to_use",
        excerpt: "产品收入结构表",
        location: {
          source_file: "测试股份有限公司招股说明书.pdf",
          page_number: 3,
          block_id: "table:T-001",
          section_path: "业务和技术",
          table_id: "T-001",
          table_title: "产品收入结构表",
          field_value: "智能控制器 / 12000万元 / 45.2%"
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
            kind: "finding",
            title: "处理结论",
            body: "当前报告由本地证据包生成，适合进行第一轮人工复核。",
            citationIds: []
          }
        ]
      },
      {
        id: "section-2",
        title: "关于公司",
        blocks: [
          {
            id: "block-2",
            kind: "finding",
            title: "关于公司",
            body: "产品收入结构表显示：智能控制器收入 12000 万元，占比 45.2%。",
            citationIds: ["C-001"]
          }
        ]
      }
    ]
  })
}));

describe("reader app", () => {
  test("renders a focused report reader with quick citation review", async () => {
    const user = userEvent.setup();

    render(<App />);
    expect(
      screen.getByRole("heading", { name: "A股招股书证据阅读台" })
    ).toBeInTheDocument();
    expect(screen.getByText("文档")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "处理结论" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "关于公司" })).toBeInTheDocument();
    expect(screen.getByText("当前报告由本地证据包生成，适合进行第一轮人工复核。")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "关于公司" }));
    expect(
      screen.getAllByText("产品收入结构表显示：智能控制器收入 12000 万元，占比 45.2%。").length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("button", { name: /查看引用 C-001/ }).length
    ).toBeGreaterThan(0);
    expect(
      screen.queryByRole("navigation", { name: "报告目录" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /查看引用 C-001/ }));
    expect(screen.getByText("引用 C-001")).toBeInTheDocument();
    expect(screen.getByText("招股说明书 第 3 页")).toBeInTheDocument();
    expect(screen.getByText("source_file")).toBeInTheDocument();
  });
});
