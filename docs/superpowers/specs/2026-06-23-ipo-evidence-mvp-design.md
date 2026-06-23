# A 股招股书证据闭环 MVP 设计

日期：2026-06-23

## 1. 目标

第一阶段只验证“证据闭环”：从本地 A 股招股书 PDF 文件夹输入，生成长期文档资产、证据包、带 citation 的长版报告，并通过本地 Web 阅读器进行纯净阅读和引用核查。

本阶段不追求完整平台形态。自动发现披露文件、PDF 下载器、港股兼容、股权结构图自动抽取、完整信息流、多公司对比和版本 diff 均后置。

## 2. 已确认决策

- 第一阶段路线：证据闭环优先。
- 输入方式：本地 PDF 文件夹，不做手动 URL 下载。
- 样本范围：A 股招股书。
- 解析方式：API 优先，后续预留本地 OCR 服务 fallback adapter。
- 报告方式：两步自动，先生成 `evidence_packet.json`，再生成 `report.md + citation.json`。
- 图结构：第一阶段只预留格式，不做股权结构图自动抽取。
- Web：最小报告阅读器，强调纯净阅读和随手核查引用。

## 3. MVP 范围

### 3.1 本阶段包含

```text
data/inbox/*.pdf
  -> ingest
  -> parser adapter
  -> TOC extractor
  -> section mapper
  -> table extractor
  -> evidence packet builder
  -> report generator
  -> citation layer
  -> web reader
```

本阶段输出：

```text
manifest.json
document.md
blocks.jsonl
source_ast.json
canonical_ast.json
tables/*.json
tables/*.csv
tables/*.md
evidence_packet.json
citation.json
report.md
parse_report.json
web_index.json
```

### 3.2 本阶段不包含

- 自动抓取官方披露源。
- PDF URL 下载器。
- 港股 Application Proof / PHIP / Prospectus 兼容。
- 股权结构图、组织架构图、产业链图自动抽取。
- 完整 AIHot 式精选、全部、待解析、已解析、黑名单导航。
- 数据库、账号、权限、云端部署。
- 多公司对比和版本差异追踪。

## 4. 目录结构

```text
IPO Evidence Intelligence/
  AGENTS.md

  configs/
    parser.yaml
    section_mapper.yaml
    scoring_rules.yaml

  data/
    inbox/
    docs/{doc_id}/
    tmp/

  src/
    ingest/
    parser/
    section_mapper/
    table_extractor/
    evidence/
    report_generator/
    citation_layer/

  web/
    app/
    components/
    lib/
    styles/

  runs/
    logs/
    evals/

  docs/
    product/
    superpowers/specs/
```

## 5. 文档包结构

```text
data/docs/{doc_id}/
  manifest.json
  document.md
  blocks.jsonl
  source_ast.json
  canonical_ast.json
  tables/
    T-001.json
    T-001.csv
    T-001.md
  evidence_packet.json
  citation.json
  report.md
  parse_report.json
  web_index.json
```

第一阶段不强制生成 `graphs/` 和 `charts/`。`manifest.json` 可预留能力声明，用于后续补充视觉对象能力。

## 6. 核心数据结构

### 6.1 manifest.json

```json
{
  "doc_id": "doc_xxx",
  "company_name": "XXX股份有限公司",
  "source_file": "XXX招股说明书.pdf",
  "source_url": null,
  "market": "a_share",
  "document_type": "招股说明书",
  "input_type": "local_pdf",
  "parse_status": "parsed",
  "report_status": "reported",
  "quality_status": "safe_to_use"
}
```

### 6.2 citation.json

第一阶段允许没有官方 URL，但必须有本地定位。

```json
{
  "citation_id": "C-001",
  "type": "text_quote",
  "source_file": "XXX招股说明书.pdf",
  "source_url": null,
  "page_number": 18,
  "block_id": "B-000231",
  "section_path": ["发行人基本情况", "主营业务"],
  "quote": "公司主要从事……",
  "summary": "公司主营业务为……"
}
```

表格引用还必须包含：

```json
{
  "citation_id": "C-014",
  "type": "table_fact",
  "table_id": "T-003",
  "table_title": "前五大客户销售情况",
  "fields": {
    "前五大客户销售金额合计": "38,200.00万元",
    "占营业收入比例": "64.3%"
  }
}
```

### 6.3 evidence_packet.json

`evidence_packet.json` 是报告生成的唯一主入口。报告生成器不应直接拿整本 Markdown 自由发挥。

证据包按研究章节组织：

```text
about_company
business_and_product
industry_and_market
customers_and_suppliers
r_and_d_and_talent
financials
use_of_proceeds
risks
```

每条 evidence 必须包含：

```text
evidence_id
canonical_section
claim_summary
source_type
source_file
page_number
block_id 或 table_id
section_path
quality_status
```

## 7. 模块职责

### 7.1 ingest

扫描 `data/inbox/`，为每个 PDF 生成 `doc_id` 和初始 `manifest.json`。文件名无法解析公司名时，先写入 `unknown_company`，后续从正文补全。

### 7.2 parser

定义统一 Parser 接口。第一实现是 API Parser，后续可接本地 OCR 服务。Parser 输出统一中间格式：

```text
document.md
blocks.jsonl
raw_tables.json
parse_report.json
```

业务模块不得直接依赖 API 原始返回。

### 7.3 section_mapper

先生成 `source_ast.json`，再映射到 `canonical_ast.json`。第一阶段覆盖 A 股常见章节，包括发行人基本情况、业务和技术、财务会计信息、募集资金、风险因素。

### 7.4 table_extractor

重点处理收入结构、客户、供应商、研发费用、募投、主要财务数据表。每张表必须有标题、章节路径、来源页码和质量评分。

### 7.5 evidence

从章节、正文块和表格中构造 `evidence_packet.json`。没有来源定位的事实不得进入证据包。

### 7.6 report_generator

基于 evidence packet 生成长版报告。报告覆盖公司、业务、行业、研发、募投、财务、风险和三类读者视角。

### 7.7 citation_layer

整理报告实际使用的引用，生成 `citation.json`，并在 `report.md` 中写入 `[C-001]` 格式编号。引用不足时报告状态为 `manual_review`。

### 7.8 web

读取本地文档包，不直接参与解析。第一阶段只提供文档列表、报告阅读、citation 面板和 Markdown 原文页。

## 8. 质量门

统一质量状态：

```text
safe_to_use
manual_review
do_not_use
```

### 8.1 解析质量

`parse_report.json` 检查文本完整率、乱码率、页数、空页比例、API 报错和表格数量。正文明显缺失或乱码率高时，整份文档标记为 `do_not_use`。

### 8.2 章节质量

`source_ast.json` 至少应识别发行人基本情况、业务和技术、财务会计信息、募集资金、风险因素中的 3 类。低于门槛时标记为 `manual_review`。

### 8.3 表格质量

表头缺失、行列错位、单位缺失的表格不得进入 evidence packet，只保留在表格目录中供人工复查。

### 8.4 引用质量

报告核心判断必须带 citation。citation 允许 `source_url: null`。文本引用不允许缺少 `source_file`、`page_number`、`block_id`、`section_path` 或 `quote`。表格引用使用 `table_id` 作为结构化对象定位，不要求 `block_id`，但不允许缺少 `source_file`、`page_number`、`table_id`、`table_title`、非空字段值或 `section_path`。

## 9. 失败处理

```text
parse_failed
  保留错误信息，不生成报告

low_quality_parse
  生成解析资产，但不生成报告

report_failed
  保留 evidence_packet，便于重新生成

citation_failed
  保留报告草稿，但不标 reported
```

系统不得删除 `data/inbox/` 中的原始 PDF。只允许清理 `data/tmp/` 中的临时文件。

## 10. Web 阅读器设计

第一阶段 Web 只做 3 个页面：

```text
/
  文档列表页

/docs/{doc_id}
  纯净报告阅读页

/docs/{doc_id}/source
  Markdown 原文页
```

### 10.1 文档列表页

展示公司名、文件名、处理状态、质量状态、报告状态、核心标签和更新时间。筛选只保留：

```text
全部
可阅读
需复核
失败
```

### 10.2 纯净报告阅读页

默认布局：

```text
顶部：公司名 / 文件状态 / 原文入口 / 目录按钮
中间：report.md 纯净正文
右侧：citation 面板
```

左侧目录不常驻。目录可以作为顶部按钮触发的临时抽屉，也可以在第一版暂缓。阅读页的默认状态应强调正文连续阅读，citation 只在需要核查时辅助。

### 10.3 Markdown 原文页

展示 `document.md`、章节目录、表格引用标记、`page_number`、`block_id` 和解析质量状态。

## 11. 技术栈

建议：

```text
处理链路：Python
Web：Vite React
数据存储：本地文件系统 + JSON/JSONL
```

第一阶段不引入数据库。后续当自动发现、搜索、多公司比较和版本追踪进入范围时，再评估数据库和索引服务。

## 12. 命令设计

处理链路实现后应提供：

```text
python -m src.ingest.scan_inbox
python -m src.pipeline.run --limit 3
python -m src.report_generator.generate --doc-id <doc_id>
```

Web 实现后应提供：

```text
npm run dev
npm run build
```

## 13. 验收标准

输入：

```text
data/inbox/ 内 3-5 份 A 股招股书 PDF
```

输出：

```text
data/docs/{doc_id}/manifest.json
data/docs/{doc_id}/document.md
data/docs/{doc_id}/blocks.jsonl
data/docs/{doc_id}/source_ast.json
data/docs/{doc_id}/canonical_ast.json
data/docs/{doc_id}/tables/*.json
data/docs/{doc_id}/evidence_packet.json
data/docs/{doc_id}/report.md
data/docs/{doc_id}/citation.json
data/docs/{doc_id}/web_index.json
```

Web：

- 文档列表可打开。
- 报告可阅读。
- citation 可点击查看。
- 表格引用可预览。
- Markdown 原文可查看。

质量：

- 至少 1 份报告达到 `safe_to_use`。
- 核心判断引用覆盖率目标为 90% 以上。
- 没有来源定位的事实不得进入最终报告。

## 14. 后续阶段

第二阶段可独立设计：

- 自动发现官方披露文件。
- PDF 下载器和官方 URL 补全。
- 港股章节兼容。
- 股权结构图半自动或自动抽取。
- 完整信息流和筛选系统。
- 本地 OCR 服务 fallback。
- 数据库和全文搜索。
