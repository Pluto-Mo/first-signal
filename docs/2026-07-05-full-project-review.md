# 2026-07-05 全项目 Review

## 范围与方法

覆盖四个区域：核心处理链路（ingest → parser → section_mapper → evidence → quality_gate → pipeline）、报告生成 + LLM 栈（skills → 草稿层 → 叙事层 → citation）、source_sync 抓取层、Web 前端 + CI，外加文档一致性与仓库卫生。全量 185 个 Python 测试通过（1.45s）。发现按严重度分级，关键断言经人工核验属实。

## 总体判断

架构方向和分层设计是对的（抓取/解析/证据/分析/写作/阅读严格分层，parser 统一接口，全链路 UTF-8，测试普遍有负例），高于个人项目平均水准。但存在一个贯穿性问题：**项目的两条立身承诺——"判断可溯源"和"不静默出假报告"——目前主要靠 prompt 约定和已经不在生产路径上的旧代码承担，生产路径上没有代码级强制**。另有约三分之一代码是多轮重构留下的死路径，文档（README/AGENTS.md）与实际实现已明显脱节。

## 高优先级（动摇核心承诺 / 正确性 / 安全）

### A. 核心承诺没有代码级执行

1. **生产报告路径没有任何 citation 校验**。唯一的校验 `_validate_citations` 困在 `report_assembler.py:47`，而 pipeline 从不调用 `assemble_report`（全仓仅测试引用）。叙事路径对"只能用给出的 citation 编号"只有 prompt 约束（`narrative_engine.py:276`），重试逻辑只查标题数和字数。LLM 输出 `[C-999]` 会原样进 report.md；`reader_bundle.py:98` 提取 citation_ids 也不做存在性检查，前端会出现悬空引用。`configs/prompts/citation_checker.yaml` 没有任何代码加载——校验层只存在于配置文件名里。
   改法：`generate_narrative` 返回前用正则提取全部编号，与合法 citation 集合求差集；有未知编号先重试、再降级 fallback。复用 `_validate_citations` 提成共享函数。

2. **quality gate 是装饰性的**（`pipeline.py:85-93`）。`apply_quality_gate` 的决策只流入 analysis_log.json；report.md 由 `generate_narrative_report` 独立生成，不读任何 gate 决策。即使所有 section 被判 `log_only`，报告照样全文输出。会出现 analysis_log 说"证据不足暂缓"、报告却照写该主题的自相矛盾。`test_pipeline.py:357` 的断言恒真，掩盖了脱节。

3. **三档质量状态在生产链路形同虚设**。四个环节叠加：`pipeline.py:117` 在 parse 前就把 manifest 硬编码为 `parsed/safe_to_use` 且之后不改；`evidence.py` 所有证据条目无条件 `safe_to_use`；`paddleocr_vl.py:152` 的质量判断仅为"有块即 safe"（scoring_rules.yaml 的 garbled_ratio 等无实现）；LLM 失败静默降级为模板报告，只在 narrative_trace.json 记 `fallback_used`，manifest 与报告本体无标记。

4. **解析 token 缺失时静默降级到 fixture 数据**（`parser/__init__.py:18-20` + `cli.py:68`）。`ipo-evidence run` 恒传 `tests/fixtures/sample_prospectus.txt`；`PADDLEOCR_API_TOKEN` 未配置时工厂静默换 `ApiStubParser`——完全忽略 PDF 内容，返回 fixture 样本 + 伪造的 `safe_to_use` parse_report。最终得到一份看似完成、实为样本数据的报告。`test_parser_factory.py:33` 还把该行为固化为预期。降级必须显式 opt-in（`--use-stub`），默认缺 token 报错；生产 CLI 不应引用 tests/ 目录。

5. **Skill fallback 产物可标 high confidence 且硬编码特定公司词表**（`skill_executor.py:316-409, 623-629`）。fallback 的产品/场景候选写死为端侧 AI 话术（"AI 芯片""智慧出行""车载"），`disclosure_gap_scan` 根本不走 LLM 而输出无证据的固定猜测；`_confidence` 只看证据质量，fallback 产物也能标 high。换任何一家非 AI 公司会产出貌似完成、实则错配的解读。给 `SkillInterpretation` 加 `llm_used/degraded` 字段，fallback 时 confidence 封顶并显式标注。

### B. 数据会被静默破坏或伪造

6. **doc_id 仅由文件名 hash 决定，同名文件静默覆盖旧证据包**（`ingest.py:11-13`，`sha256(path.name)`）。同名不同内容（新旧申报稿）同 doc_id，`run_one` 直接覆盖，旧资产无提示丢失；改名（含大小写）则重复处理。inbox 里已有 `思必驰科技股份有限公司  .pdf`（文件名含两个尾随空格）这类脆弱输入。manifest 应记录内容 hash，检测到不一致时报错而非覆盖。

7. **数字开头的正文被误判为标题**（`section_mapper.py:21` 最后一条 heading 正则，经实际运行验证）。`"2023年，公司实现营业收入12,000万元。"` 被判为 level-1 标题，三重后果：后续所有块的 section_path 被污染（citation 章节定位错误）、该句被 `_is_heading_only` 静默排除出证据包、AST 层级错乱。招股书中此类句式极常见。正则改为数字编号后必须跟分隔符：`^(\d+(?:\.\d+)*)(?:[、.．]|\s)\s*(.+)$`，并补负例测试。

8. **表格证据溯源失真**：所有 parser raw_tables 的 section_path 硬编码 `["业务和技术"]`、缺失页码静默置 1（`pipeline.py:130`、`table_extractor.py:17-26`）——citation 会声称"业务和技术、第1页"而实际都不是，这是伪造定位。另外 `evidence.py:316-456` 对全数值列一律跨行求和生成"X合计"证据（毛利率列产出"合计150%"、年份列产出"合计6069"），原表并无此行，citation 核对不出。rowspan/colspan 表格被静默丢弃、行数截断至 12 也无任何记录（`evidence.py:117,165`）。

9. **paddle 解析页码来自"JSONL 行号=页码"的未验证假设**（`paddleocr_vl.py:92`）。若一行不严格对应一页，全部 block/证据/citation 页码整体错位，溯源全毁且难察觉。需核实 API 响应中的真实页码字段，至少加多页 fixture 测试固定假设。

10. **run_one 覆盖人工修正**（`pipeline.py:113-152` vs `ingest.py:43-45`）。`scan_inbox` 和 `regenerate_report` 刻意保留 manifest 人工字段和 report_inputs 手工编辑（且有测试保障），`run_one` 却无条件重建覆盖。重跑一次 run 静默清掉所有人工调整。

### C. 抓取层的中断安全

11. **单个候选下载失败中止整个 run，丢失全部留档**（`source_sync/service.py:51-55` + `source_sync/cli.py:48-89`）。下载循环无 per-candidate 异常隔离，而 discovery/filter/download 日志和 state 全在 `run_sync` 返回后才写。一次网络抖动 = 本次所有被过滤样本零留档（直接违反"被过滤样本必须留记录"）+ 已下载 PDF 不进 state、下次重复下载。留档写入应提前到下载前，下载逐个 try/except。主 CLI 的批处理同样无失败隔离（`cli.py:70-72`，一个 PDF 失败中断整批）。

12. **PDF 下载无内容校验、无自定义头、非原子写入**（`source_sync/downloader.py:16-36`）。用 python-requests 默认 UA（最易被风控）；对方返回 200 的 HTML 验证页会被原样存成 `.pdf` 进入解析链路（inbox 文件按约定不可自动删除，污染持久）；`write_bytes` 直写最终路径，中断留半个 PDF；数百 MB 文件全量进内存。改法：复用配置的 headers、校验 `%PDF-` 魔数、`stream=True` 分块写 `.part` 再原子改名。

### D. 安全

13. **提示注入 → 密钥外泄路径真实存在**（`llm_caller.py:27-47`）。agent 以 `--cd repo_root()` + read-only 运行，可读整个仓库含 `.env`；`cli.py:83` 的 `load_dotenv` 已把 token 注入环境且子进程未过滤 env。招股书文本（外部输入）进 prompt，注入指令可诱导 agent 把 token 写进输出 → report.md → gh-pages 公开。改法：`--cd` 指向 `data/docs/<doc_id>` 等受限目录；`subprocess.run(env=...)` 剔除敏感变量；对 report.md 加简单 secret 扫描。改动很小，建议尽快。
    （前端 XSS 已确认干净：全部内容经 JSX 文本节点渲染，无 dangerouslySetInnerHTML。）

14. **LLM 调用健壮性缺口**：`llm_caller.py:21` `del max_tokens`——所有调用方传的 token 上限被静默丢弃，成本与输出实际无上限，`test_llm_caller.py:82` 测的是假接口；skill/narrative 层的 except 不含 `FileNotFoundError/OSError/UnicodeDecodeError`（codex 不在 PATH 是最常见故障），会绕过 fallback 直接炸掉 pipeline（`skill_executor.py:150` 等、`narrative_engine.py:105`）。在 `call_agent_for_narrative` 内统一包装为 RuntimeError 即可全覆盖。

## 中优先级

15. **死配置与配置漂移**：`configs/section_mapper.yaml`、`configs/scoring_rules.yaml` 全项目无代码读取（规则硬编码在 `section_mapper.py:8` 的 CANONICAL_RULES 和 `evidence.py:515`）；canonical 章节定义存在三套并行且互不一致；`source_sync.yaml` 的 window/limits/jitter 无人读（真实默认硬编码在 `source_sync/cli.py:26`，数值巧合一致）；`filter_rules.yaml` 的 `action` 字段不参与决策；`configs/skills/*.yaml` 的 output_schema 无消费者且已与代码输出漂移；`report_prompt.yaml` 的 writing_prompt 块（含"没有来源定位的事实不得进入最终报告"这条核心纪律）没有任何代码读取。收敛为单一事实来源：要么代码读配置、要么删配置留代码。

16. **jitter 未实现**：请求是精确 2.0s 固定节奏，比带抖动更像机器人，与"避免高风控行为"相反（`source_sync/cli.py` 节流处加 `random.uniform`）。

17. **client 硬编码排除词让 `body_title_exclude` 配置失效，且被它筛掉的公告零留档**（`source_sync/client.py:14-26,101-108`）；过滤留档放在按约定"可清理"的 data/tmp 下，一旦清理被过滤样本彻底不可回捞（`source_sync.yaml:13`，建议迁 `runs/logs/` 或在 AGENTS.md 豁免）。

18. **非原子写贯穿全项目**（`io.py:15-34`、`source_sync/state.py:17`）：manifest/evidence_packet/sync_state 都是直写覆盖，进程中断留半截 JSON；state 损坏后 sync 整体瘫痪。统一改临时文件 + `os.replace`。`regenerate_report` 还先写 manifest="reported" 再生成六份工件（`pipeline.py:180`），中途失败后 manifest 与工件不同步——应先内存生成、全部成功再落盘。

19. **reader_bundle 97% 是死数据**：实测 6 个 bundle 各含 638-1188 条 citation，正文实际引用仅 12-24 条；单文档最大 1.9MB、近半为死重，showcase-data 共 7.5MB。生成侧只输出被引用的 citation（完整清单留 citation.json），体积近乎减半，加载时间等比下降。改动小收益大。

20. **前端状态机三处问题**（`web/src/App.tsx`）：切换文档时已下载的 bundle 被丢弃、切回需整包重下（`:83-90`，写缓存不需要 isActive 守卫）；fetch 失败后点同一文档不触发重试、错误横幅挂在别的文档上不消失（`:67-79,142-145`）；JSON 无运行时校验 + 无 ErrorBoundary，schema 漂移直接白屏（`lib/api.ts:17` 纯 `as T` 断言）。

21. **CI 从不跑测试**（`.github/workflows/pages.yml`）：vitest 和 pytest 都存在，但唯一的 workflow 只 build 不 test，测试挂了照样部署。加 test 步骤（Python + web），顺手加 `paths` 过滤避免改 README 也触发部署。

22. **叙事层 citation 只到 skill 粒度**：编号合法但"张冠李戴"（某编号的证据未必支持它所贴的句子）当前架构零检测（`narrative_engine.py:187-251`）。短期在文档明确这一已知边界，中期让 skill 输出按字段划分 evidence_id 子集。

## 死代码 / 死路径清单（多轮重构遗留，估计约占代码量三分之一）

| 项 | 证据 | 建议 |
|---|---|---|
| `report_assembler.assemble_report` 全模块 | 仅测试引用；唯一的 citation 强校验困在其中 | 提取 `_validate_citations` 后删除 |
| `report_generator.py` 模板报告路径约 550 行（`_report_body`、KEYWORDS 含"比亚迪/华为/DUI中台"、LOW_VALUE_SNIPPETS、SECTION_ORDER） | pipeline 只走 narrative 路径 | 删除及配套测试 |
| `section_generator.py` + `section_writer.py` 草稿流水线 | draft 正文被丢弃，只喂 analysis_log | 与发现 2 一并决策 |
| `configs/prompts/citation_checker.yaml`、`stitch_writer.yaml` | 无生产代码加载 | 实现或删除 |
| `configs/report_profiles/` 三个非 base profile | `default_report_profile_key` 恒返回 "base" | 删除或注明预留 |
| `configs/section_mapper.yaml`、`scoring_rules.yaml`、`parser.yaml` 部分键、`source_sync.yaml` 半数键 | 无代码读取 | 见发现 15 |
| `narrative_engine._build_debug_prompt`、`paths.doc_dir`、`web_index` 双写（`pipeline.py:105,152`）、前端 `DocumentList.tsx`/App 冗余 effect/`has-drawer` class | 零调用方 | 删除 |
| `web_index.py:178-187`、`web/src/lib/grouping.ts:145-158` 行业推断硬编码"思必驰/永励"，前后端各一份 | 换公司即失效或误分类 | 行业只信 manifest/index 字段，前端 fallback"未分类" |

## 文档与现实脱节

23. **README 快速开始的命令跑不通**：`python -m ipo_evidence.cli sync-a-share` 和 `build-web-index` 子命令不存在（实际只有 scan-inbox/run/generate-report；sync 的真实入口是 `python -m ipo_evidence.source_sync.cli sync-a-share`）。
24. **AGENTS.md 整体过期**：目录约定写的是 `src/ingest/` 等旧结构（实际为 `src/ipo_evidence/` 平铺包）；验证命令 `python -m src.pipeline.run` 等全部失效。按"先改文档再改实践"的原则应尽快对齐。
25. **三份几乎相同的 README**：`README.github.md` 与 `docs/README-new.md` 完全相同（diff 为空），与 `README.md` 仅差 25 行。保留 README.md，另两份删除。
26. **LLM 后端名不符实**：README 写"Claude/Anthropic API"，实际是 codex CLI 子进程（`llm_caller.py:18`，函数名 `call_claude_for_skill` 同样误导）。改名 `call_llm_for_skill` 并在 README 澄清。

## 仓库卫生

- `.tmp/` 未跟踪且不在 .gitignore（gitignore 只有 `data/tmp`），内含会话级日志/截图，应加入 ignore。
- 本地 8 个已合并分支（codex/*、report-inputs-architecture）+ 多个远端旧分支可清理（删除需用户确认）。
- 临时文件泄漏：`llm_caller.py:23` `NamedTemporaryFile(delete=False)` 用后不删，finally 中 unlink。
- citation 编号正则 `C-\d{3}` 假定 ≤999 条证据，第 1000 条起被静默丢弃（`report_assembler.py:9`、`reader_bundle.py:19`，改 `C-\d{3,}`）。
- 根 package.json 合理可留，建议加 `"private": true`。
- showcase-data 7.5MB 进 git 现阶段可接受；展示文档到 15-20 个或频繁整批更新时再迁出（配合发现 19 先减半）。

## 测试评估

185 个测试全过且多数是真测试（幂等、失败传播、负例都有覆盖）。缺口与漏网 bug 一一对应：section_mapper 无数字开头正文负例（发现 7 的逃逸原因）；stub 静默降级被测成正确行为（发现 4）；`test_pipeline.py:357` 恒真断言（发现 2）；无 doc_id 冲突用例（发现 6）；LLM 侧无未知 citation 编号、无 FileNotFoundError、无"合法 JSON 但字段类型错"用例（`_compact_list` 会静默吞掉类型错误的字段，报告悄悄缺内容不触发 fallback）；`source_sync/client.py` 零测试（恰是最脆弱模块）；前端无错误路径与缓存行为测试。

## 建议行动顺序

1. **发现 13**（注入→泄密：换 --cd + 过滤 env，改动最小）和**发现 7**（标题正则一行 + 测试，收益最大）。
2. **发现 1**（citation 代码级校验——项目立身之本）+ **发现 4**（去掉 stub 静默降级）+ **发现 14**（fallback 补 OSError）。
3. **死代码大清扫**（上表一次删完，代码量约减三分之一，发现 2/5/15 的一半问题随之消失或变容易）。
4. **发现 11/12/18**（"中断安全"一族：留档前置、原子写、PDF 校验，一批改完）。
5. **发现 3/6/8/10**（质量状态真实化 + doc_id 内容 hash + 表格溯源诚实化）。
6. 文档对齐（23-26）+ CI 加测试（21）+ bundle 瘦身（19）+ 前端状态修复（20）。
