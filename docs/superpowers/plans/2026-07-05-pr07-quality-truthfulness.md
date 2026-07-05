# PR-07 质量状态真实化 + quality gate 接线

分支名：`fix/quality-truthfulness`　规模：大　依赖：PR-03（citation 校验已在叙事路径就位）
背景：review 发现 #2、#3、#5（`docs/2026-07-05-full-project-review.md`）。三档质量状态（safe_to_use/manual_review/do_not_use）目前在生产链路形同虚设；quality gate 的决策只进 analysis_log，正文报告完全绕过它。

## 架构决策（已定，执行者不要另行发散）

叙事路径（generate_narrative_report）是唯一正文引擎。quality gate 改为直接基于 evidence packet 与 skills 输出做决策，并让叙事路径消费决策。草稿流水线（section_generator/section_writer）在本 PR 后不再是 gate 的数据源（其删除在 PR-09 执行，本 PR 不删文件）。

## 改动清单

1. **gate 输入重构**（`quality_gate.py` + `pipeline.py:85-93`）：`apply_quality_gate` 的证据统计（fact_count/strength）改为直接从 evidence_packet 与 skill 输出计算，不再依赖 drafts；`evidence_policy`（min_fact_count/min_strength）继续从 report_inputs 读取。
2. **叙事路径消费 gate 决策**（`narrative_engine.py`）：被判 `log_only` 的 section/skill 材料不进入 narrative prompt；prompt 中加入指令：对证据不足的主题输出明确的"证据不足，暂不展开"披露而非硬写；analysis_log 与叙事报告不得再互相矛盾。
3. **manifest 状态传导**（`pipeline.py:117-119`）：删除"parse 前硬编码 parsed/safe_to_use"。改为：parse 完成后按 parse_report.quality_status 写入；报告生成后若 `fallback_used=true` → manifest.quality_status 降为 `manual_review`。
4. **解析质量评分接线**（`parser/paddleocr_vl.py:152` + `configs/scoring_rules.yaml`）：实现 scoring_rules.yaml 中已定义的简化版阈值——`garbled_ratio`（非常见字符占比）与 `min_non_empty_pages`，超标时 parse_report.quality_status 为 manual_review/do_not_use 并记录原因。yaml 成为该逻辑的唯一配置来源（这样 PR-09 清扫时保留此文件）。
5. **证据条目质量挂钩**（`evidence.py`）：不再无条件 `safe_to_use`——表格证据 quality_score < 0.75（阈值从 scoring_rules.yaml 读，删除 evidence.py:515 硬编码）或 page_number 为 None → `manual_review`。
6. **fallback 诚实化**（`skill_executor.py`）：
   - `SkillInterpretation` 增加 `llm_used: bool` 字段；
   - fallback 产物 confidence 封顶 `medium`（`_confidence` 当前只看证据质量，fallback 也能标 high）；
   - `disclosure_gap_scan` 的固定猜测 `possible_reasons`（无证据）删除或明确标注为"推测（无证据）"；
   - fallback 使用情况写入 analysis_log，且 report.md 头部插入质量横幅（如"⚠ 本报告部分内容由降级模板生成，未经 LLM 分析，状态：manual_review"）。
7. **修恒真断言**（`tests/test_pipeline.py:357`）：`"公司介绍与行业概况" not in report_text` 对叙事报告恒真。改为构造可证伪场景：某 section 被判 log_only 后，其 skill 材料确实未进入 narrative prompt（可断言 mock LLM 收到的 prompt 内容）。

## 验收标准

- 缺 token / codex 不可用走全 fallback 时：manifest.quality_status == manual_review，report.md 含质量横幅。
- 全部 section 判 log_only 时：narrative prompt 不含这些 section 的 skill 材料。
- 表格 quality_score 低的证据条目状态为 manual_review。
- 全量 pytest 通过（含新增用例）。

## 验证

```bash
python -m pytest -q
```
