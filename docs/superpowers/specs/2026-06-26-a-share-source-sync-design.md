# A 股抓取前置层与 OCR 对接设计

日期：2026-06-26

## 1. 目标

在不改动现有证据包、报告生成和 Web 阅读架构的前提下，为项目补上一层 A 股招股说明书自动抓取前置层。第一步目标不是做完整信息流，而是小规模真实抓取联调：把少量真实正文 PDF 下载到 `data/inbox/`，并把后续 OCR API 所需的边界字段、过滤规则和状态记录接好。

本设计只覆盖 A 股。港股兼容会在后续独立设计中处理。

## 2. 已确认决策

- 现有本地 OCR API 已测试通过，本轮不重新设计 OCR。
- 第一轮只做 A 股真实抓取联调，不做港股。
- 本轮不直接跑 OCR，但抓取产物必须为后续 OCR 调用准备完整边界字段。
- 报告继续后台预生成，不改成懒生成。
- `data/inbox/` 继续作为进入主处理链路的统一 PDF 入口。
- 被过滤的样本不下载正文 PDF，但必须留记录，方便后续回捞和调规则。
- 不做大行业黑名单，不做白名单。
- 筛选逻辑以可配置规则为主，不把 token 筛选放进主流程。

## 3. 范围

### 3.1 本轮包含

```text
cninfo source
  -> candidate discovery
  -> narrow filter rules
  -> filtered/discovery logs
  -> pdf download
  -> data/inbox/*.pdf
  -> existing scan-inbox / run pipeline
```

本轮产物：

```text
configs/source_sync.yaml
configs/filter_rules.yaml
data/tmp/source_sync/discovery_log.jsonl
data/tmp/source_sync/filter_log.jsonl
data/tmp/source_sync/download_log.jsonl
data/tmp/source_sync/sync_state.json
data/inbox/*.pdf
```

### 3.2 本轮不包含

- 港股招股书抓取与 OCR 兼容。
- 交易所官方时间线的完整对账。
- 高频调度、秒级抓取、复杂任务编排。
- 模型参与主筛选。
- 抓取后自动触发全量 OCR。

## 4. 设计原则

### 4.1 抓取层与处理层解耦

抓取层只负责：

- 发现候选公告
- 规则筛选
- 下载 PDF
- 写状态和日志

抓取层不得直接修改：

- OCR parser 接口
- evidence packet 结构
- report generator 逻辑
- Web reader 逻辑

### 4.2 低频低并发

外部自动化可以按小时级触发，但抓取实现内部必须保持低频、低并发，避免秒级轮询和高风控行为。第一版默认串行下载或极低并发下载，并支持随机抖动和小窗口回看。

### 4.3 规则优先

主流程不使用 token 筛选。筛选靠标题、行业字段、公司简介和披露阶段做窄规则打分。后续如果需要 AI 辅助，只处理观察池，不进入默认链路。

### 4.4 可回滚

被过滤样本不能静默丢弃。所有候选、过滤和下载结果都要落日志，便于回放、调规则和回捞。

## 5. 输入源与抓取口径

### 5.1 主抓取源

第一版 A 股主抓取源使用巨潮资讯的两段式免费接口。

原因：

- `data20/ipoProspectus/getIpoProspectus` 能提供更接近上市进程列表的最新候选池，附带行业、披露阶段和公司简介等筛选字段。
- `new/hisAnnouncement/query` 能补齐正文 PDF 公告与公告 ID，便于做“只抓正文、不抓提示性公告”的二次确认。
- 两段式方案比单纯按字段全文搜公告更稳，也更符合“尽量不缺 PDF”的目标。

### 5.2 正文 PDF 口径

只下载正文招股说明书 PDF，不下载：

- 提示性公告
- 摘要
- 英文版
- 更正公告
- 问询回复
- 法律意见书
- 审计报告
- 其他非正文附件

同一家公司命中多份正文时，第一版只保留最新一版正文 PDF 进入 `data/inbox/`。

### 5.3 时间窗口

第一版使用小时间窗口抓取，例如最近 `3-7` 天，或者“自上次同步以来 + 回看 3 天”的重叠窗口。这样既控制流量，也能覆盖迟到披露。

## 6. 目录与文件

### 6.1 新增配置

```text
configs/source_sync.yaml
configs/filter_rules.yaml
```

### 6.2 新增状态目录

```text
data/tmp/source_sync/
  discovery_log.jsonl
  filter_log.jsonl
  download_log.jsonl
  sync_state.json
```

### 6.3 现有入口保持不变

```text
data/inbox/
```

所有被放行且下载成功的正文 PDF，都直接写入 `data/inbox/`，继续由现有 `scan-inbox -> run` 链路处理。

## 7. 模块边界

建议新增模块：

```text
src/ipo_evidence/source_sync/
  client.py
  filters.py
  downloader.py
  state.py
  cli.py
```

### 7.1 client

负责源站请求、候选发现、字段归一化。

第一版 client 采用两步：

- 先从 `ipoProspectus` 列表接口按时间倒序发现候选公司与阶段信息。
- 再按 `company_name + 招股说明书` 或 `security_code + 招股说明书` 查询公告接口，补齐正文 PDF 地址与公告 ID。

### 7.2 filters

负责标题正文过滤、窄规则打分、观察池判定。

### 7.3 downloader

负责下载 PDF、命名、去重、写入 `data/inbox/`。

### 7.4 state

负责同步状态、日志、恢复和去重索引。

### 7.5 cli

提供小规模联调命令，不直接触发 OCR。

## 8. 筛选规则设计

### 8.1 规则输入字段

筛选时使用以下字段组合判断：

- `company_name`
- `announcement_title`
- `industry_text`
- `company_summary`
- `disclosure_stage`

不依赖单独的公司名判断。

### 8.2 规则结果

规则输出三类结果：

```text
allow
observe
filter
```

第一版处理方式：

- `allow`：下载进入 `data/inbox/`
- `observe`：本轮为了先跑通，也下载进入 `data/inbox/`，但额外记录观察标签
- `filter`：不下载，仅记录原因

### 8.3 规则风格

不做大行业一刀切黑名单。规则必须更窄、更垂直，优先识别：

- 特别专业且垂直细分的领域
- 医药中的特定方向
- 材料中的特定工艺或上游专用品类

规则采用“专业硬词加分 + 商业缓冲词减分”的方式，避免因为出现大行业词就误伤。

### 8.4 观察池

观察池不单独存放 PDF，第一版只额外记录状态与命中原因。这样主链先跑通，后续再决定是否分层缓存。

## 9. OCR 对接边界

本轮不调用 OCR，但抓取层必须为后续 OCR 预留完整输入字段。每个下载成功的样本，都应在状态记录中保留：

- `local_pdf_path`
- `company_name`
- `market`
- `exchange`
- `announcement_id`
- `announcement_title`
- `published_at`
- `source_url`
- `disclosure_stage`
- `file_sha256`
- `ocr_status`

推荐状态流转：

```text
discovered
filtered
downloaded
ocr_not_started
ocr_processing
ocr_done
ocr_failed
```

现有 `parser.yaml`、`create_parser()` 和 `PaddleOCRVLParser` 继续作为 OCR 层实现。抓取层只需要把 PDF 和元数据交给现有处理链，不反向依赖 OCR 返回格式。

## 10. 去重策略

### 10.1 候选去重

以以下字段组合构建候选唯一键：

```text
announcement_id
or
company_name + announcement_title + published_at
```

### 10.2 文件去重

下载成功后计算 `sha256`。如果本地已存在同 hash 文件，写去重日志，不重复落盘。

### 10.3 公司级最新版本

同一家公司命中多份正文时，只将最新正文 PDF 作为正式下载目标。旧版本记录保留在日志里，不进入 `data/inbox/`。

## 11. 日志与状态

### 11.1 discovery_log.jsonl

记录所有发现到的候选，不管后续是否下载。

### 11.2 filter_log.jsonl

记录被过滤和观察池样本，至少包含：

- `sync_id`
- `company_name`
- `security_code`
- `announcement_title`
- `published_at`
- `industry_text`
- `company_summary`
- `source_url`
- `decision`
- `matched_rules`
- `matched_terms`
- `score`
- `reason`
- `restorable`

### 11.3 download_log.jsonl

记录下载结果，至少包含：

- `sync_id`
- `company_name`
- `announcement_id`
- `local_pdf_path`
- `file_sha256`
- `download_status`
- `downloaded_at`

### 11.4 sync_state.json

记录最近一次成功同步窗口、最近处理公告、重叠回看配置和限频参数。

## 12. 命令设计

第一版抓取联调命令建议为：

```text
python -m ipo_evidence.source_sync.cli sync-a-share --days 7 --limit 3
```

行为：

- 发现少量 A 股候选
- 执行筛选
- 下载正文 PDF 到 `data/inbox/`
- 写 discovery/filter/download 状态日志
- 不自动执行 OCR

现有命令保持不变：

```text
python -m ipo_evidence.cli scan-inbox
python -m ipo_evidence.cli run --limit 3
python -m ipo_evidence.cli generate-report --doc-id <doc_id>
```

## 13. 测试策略

### 13.1 第一轮真实联调测试

目标：

- 能发现少量 A 股真实候选
- 能正确过滤非正文
- 能下载至少 1-3 份真实正文 PDF 到 `data/inbox/`
- 能写出完整状态记录

本轮不要求：

- 自动跑 OCR
- 自动生成报告
- 交易所时间线全量校验

### 13.2 自动化测试

至少覆盖：

- 候选归一化
- 正文过滤规则
- 过滤规则打分
- 去重逻辑
- 状态日志落盘

网络联调测试与纯单元测试分开，避免让常规测试依赖外网。

## 14. 风险与后续

### 14.1 当前风险

- 巨潮字段和前端接口可能变更。
- 第一版规则词表不可能一次到位，误杀与漏放都会存在。
- A 股先跑通后，港股仍需要独立章节和 OCR 口径适配。

### 14.2 后续阶段

- 增加交易所官方一致性校验。
- 调整过滤规则词表与观察池策略。
- 接入抓取后自动 OCR 的受控任务流。
- 设计港股抓取与 OCR 兼容。
