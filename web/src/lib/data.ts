import type { Citation, DocumentRecord } from "./types";

const alphaCitations: Citation[] = [
  {
    id: "CITE-001",
    label: "主营收入结构",
    summary: "核心收入集中于工业自动化设备与配套服务，收入构成相对稳定。",
    quality: "safe_to_use",
    excerpt:
      "报告期内，公司主营业务收入主要来自工业自动化设备及配套服务，两类收入合计占主营业务收入比重均超过 90%。",
    location: {
      source_file: "alpha-prospectus.pdf",
      page_number: 78,
      block_id: "B-078-03",
      section_path: "第三节/业务与技术/主营业务",
      table_id: "T-001",
      table_title: "主营业务收入构成",
      field_value: "工业自动化设备 72.4%"
    }
  },
  {
    id: "CITE-002",
    label: "产能利用率",
    summary: "主要产线利用率维持高位，扩产需求来自既有订单积压。",
    quality: "manual_review",
    excerpt:
      "2023 年主要产品产能利用率达到 92.6%，公司拟通过募投项目扩充装配与测试环节产能。",
    location: {
      source_file: "alpha-prospectus.pdf",
      page_number: 126,
      block_id: "B-126-07",
      section_path: "第九节/募集资金运用/产能扩张必要性"
    }
  },
  {
    id: "CITE-003",
    label: "客户集中度",
    summary: "前五大客户占比偏高，但客户结构未出现单一客户依赖。",
    quality: "safe_to_use",
    excerpt:
      "报告期各期前五大客户销售收入占比分别为 46.8%、44.2% 和 41.9%，不存在对单一客户重大依赖。",
    location: {
      source_file: "alpha-prospectus.pdf",
      page_number: 95,
      block_id: "B-095-02",
      section_path: "第五节/业务与技术/销售情况"
    }
  }
];

export const documents: DocumentRecord[] = [
  {
    id: "alpha-tech",
    companyName: "华晟精控",
    exchange: "深交所创业板",
    reportTitle: "华晟精控招股书证据解读",
    reportDate: "2026-06-23",
    quality: "safe_to_use",
    citations: alphaCitations,
    sections: [
      {
        id: "business-tech",
        title: "业务与技术",
        blocks: [
          {
            id: "block-1",
            kind: "lead",
            title: "核心判断",
            body:
              "公司收入基础来自成熟产品线，业务连续性较强，但扩产叙事需要结合产能利用率与订单可验证性一起看。",
            citationIds: ["CITE-001", "CITE-002"]
          },
          {
            id: "block-2",
            kind: "finding",
            title: "阅读提示",
            body:
              "正文保留连续阅读感，关键证据只在句尾挂引用，适合先通读判断，再在右侧面板回看来源细节。",
            citationIds: ["CITE-001"]
          }
        ]
      },
      {
        id: "customers",
        title: "客户与订单",
        blocks: [
          {
            id: "block-3",
            kind: "finding",
            title: "客户集中度",
            body:
              "前五大客户占比仍高，但从披露口径看，并没有落到单一客户依赖的风险结构。",
            citationIds: ["CITE-003"]
          },
          {
            id: "block-4",
            kind: "note",
            body:
              "这一段更适合结合订单持续性与回款节奏继续人工复核，尤其是新增大客户的验证材料是否充分。",
            citationIds: ["CITE-003"]
          }
        ]
      }
    ]
  },
  {
    id: "beta-med",
    companyName: "安序生物",
    exchange: "上交所科创板",
    reportTitle: "安序生物招股书证据解读",
    reportDate: "2026-06-20",
    quality: "manual_review",
    citations: [
      {
        id: "CITE-101",
        label: "研发投入率",
        summary: "研发投入率处于可比公司中位偏上，但资本化政策仍需单独复核。",
        quality: "manual_review",
        excerpt:
          "报告期各期研发投入占营业收入比例分别为 18.2%、19.7% 和 21.1%。",
        location: {
          source_file: "beta-prospectus.pdf",
          page_number: 142,
          block_id: "B-142-04",
          section_path: "第六节/研发与技术/研发投入"
        }
      }
    ],
    sections: [
      {
        id: "rnd",
        title: "研发投入",
        blocks: [
          {
            id: "block-5",
            kind: "lead",
            title: "核心判断",
            body:
              "研发投入率本身不弱，但资本化口径和项目进度的对应关系还需要继续核。",
            citationIds: ["CITE-101"]
          }
        ]
      }
    ]
  }
];

export function getDocumentById(documentId: string): DocumentRecord {
  const match = documents.find((document) => document.id === documentId);

  if (!match) {
    return documents[0];
  }

  return match;
}
