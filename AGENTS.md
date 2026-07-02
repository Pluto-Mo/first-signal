# AGENTS.md

## 项目定位

本项目是个人使用的招股书证据型解读系统。第一阶段目标已经完成：从本地 PDF 文件夹跑通证据闭环，让 PDF 解析为长期文档资产，生成可核查引用的长版报告，并在本地 Web 阅读器中阅读和核查 citation。

当前阶段进入第二阶段的前半段：在不破坏现有处理链路的前提下，补上自动抓取前置层，并逐步推进港股兼容。当前实现顺序先做 A 股真实抓取与下载联调，再做港股输入兼容和后续口径补齐。

## 沟通和工作原则

- 默认使用中文沟通。
- 代码、命令、变量名、文件名使用英文。
- 结论先行，再解释理由。
- 信息不足时区分事实、假设、判断和风险。
- 未经确认不得扩大当前阶段范围。
- 大改动前先给方案，确认后再动手。

## 红线

以下操作必须先问用户：

- 删除文件、目录或 git 历史。
- 修改 `.env`、密钥、token、CI/CD 配置。
- 数据库 schema 变更或数据迁移。
- `git push`、`git rebase`、`git reset --hard`、强制推送。
- 安装新的全局依赖或修改系统配置。
- 公开发布、部署生产环境、发布文章或包。

## 目录约定

```text
configs/
  parser.yaml
  section_mapper.yaml
  scoring_rules.yaml
  source_sync.yaml
  filter_rules.yaml

data/
  inbox/
  docs/
  tmp/

src/
  ingest/
  parser/
  section_mapper/
  table_extractor/
  evidence/
  report_generator/
  citation_layer/
  source_sync/

web/
  app/
  components/
  lib/
  styles/

runs/
  logs/
  evals/

docs/
  report_generation_architecture.md
  product/
  superpowers/specs/
```

## 文件生命周期

- `data/inbox/` 存放进入主处理链路的初始 PDF，既可以是用户手动放入，也可以是自动抓取后写入。系统不得自动删除这里的文件。
- `data/tmp/` 存放临时解析文件、抓取状态、过滤记录和其他可重建缓存，可以由清理命令清理。
- `data/docs/{doc_id}/` 存放长期文档资产，包括 Markdown、AST、表格、证据包、报告和 citation。
- PDF 是输入材料，不是长期知识资产。
- 长期资产以 Markdown、JSON、JSONL、CSV 为主。

## 文档包约定

每份文档输出到：

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
  analysis_log.json
  quality_notes.md
  citation.json
  report.md
  parse_report.json
  web_index.json
```

第一阶段不强制生成 `graphs/`、`charts/`、`analysis_log.json` 和 `quality_notes.md`，但数据模型应允许后续扩展。

`analysis_log.json` 和 `quality_notes.md` 用于记录证据不足、被合并或暂缓进入正文的内部分析事项；这些内容不得伪装成最终报告结论。

## 引用约定

- 报告里的核心判断必须带 citation 编号。
- citation 允许 `source_url: null`，但必须包含本地定位字段。
- 文本引用必须包含 `source_file`、`page_number`、`block_id`、`section_path` 和 `quote`。
- 表格引用使用 `table_id` 作为结构化对象定位，不要求 `block_id`。
- 表格引用必须包含 `source_file`、`page_number`、`table_id`、`table_title`、非空字段值和 `section_path`。
- 没有来源定位的事实不得进入最终报告。

## 质量状态

统一使用三档质量状态：

```text
safe_to_use
manual_review
do_not_use
```

解析失败、引用不足、表格质量低或章节结构不完整时，应明确记录状态和原因，不得静默生成看似完成的报告。

## 技术约定

- 第一阶段处理链路优先使用 Python。
- 第一阶段 Web 阅读器优先使用 Vite React。
- 当前阶段数据存储继续使用本地文件系统和 JSON/JSONL，不引入数据库。
- Parser 必须通过统一接口接入，API Parser 优先，本地 OCR 服务作为后续 fallback adapter。
- 业务逻辑不得直接依赖某个解析 API 的原始返回格式。
- 自动抓取层必须与 OCR/解析层解耦。抓取层只负责发现、筛选、下载、留档和状态管理，不得直接改写证据包、报告生成或 Web 阅读逻辑。
- 报告必须后台预生成，禁止改成按打开页面时临时生成。
- 自动抓取默认低频、低并发运行，避免秒级抓取和高风控行为。
- 过滤规则优先使用可配置规则，不使用大行业一刀切黑名单。被过滤样本必须留记录，便于后续回捞和调规则。

## 验证约定

实现代码后，每次改动应按影响范围主动验证。

当前设计阶段可用验证：

```text
git status --short
```

处理链路实现后应提供并维护：

```text
python -m src.ingest.scan_inbox
python -m src.pipeline.run --limit 3
python -m src.report_generator.generate --doc-id <doc_id>
```

自动抓取前置层实现后应提供并维护：

```text
python -m src.source_sync.sync_a_share --days 7 --limit 3
```

Web 实现后应提供并维护：

```text
npm run dev
npm run build
```

如果验证命令尚未实现，最终回复中必须说明未运行的原因。

## 范围控制

当前阶段继续保留并维护：

- 本地 PDF 文件夹输入。
- A 股招股书样本。
- API 优先的 PDF 解析适配层。
- Markdown、blocks、source AST、canonical AST。
- 重点表格结构化。
- evidence packet。
- report.md 和 citation.json。
- 最小 Web 报告阅读页和 citation 面板。

当前阶段新增：

- A 股招股书自动抓取前置层。
- 自动抓取的黑名单/观察池规则和留档。
- 抓取层与 OCR API 对接边界字段。
- 少量真实样本的抓取联调测试。

当前阶段暂缓：

- 高频定时抓取和复杂调度。
- 港股 OCR 口径合并与后处理兼容。
- 股权结构图自动抽取。
- 完整 AIHot 式信息流。
- 多公司横向对比。
- 版本 diff。
- 复杂图谱探索。
