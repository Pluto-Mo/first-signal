# 报告拼接层执行修订

本文是对报告拼接层执行文档的 review 后修订稿。目标是把执行边界收得更清楚：最终 `report.md` 只接收质量门通过的 `SectionDraft`，完成度不足的内容进入 `analysis_log.json`，而不是在读者可见报告里暴露缺口。

## 1. 本阶段目标

本阶段只实现确定性的本地拼接层，不引入新的 LLM 调用、不接外部证据、不做行业 profile 选择，也不删除旧的 `report_generator.py`。

主链路应调整为：

```text
section_drafts + quality_decisions -> report assembly -> report.md
```

执行重点是让 `pipeline` 的最终报告来源从 legacy 长文生成器切换到 section draft contract，同时继续保持：

- `citation.json` 仍从 `evidence_packet` 生成；
- `reader_bundle.json` 仍从最终 `report.md` 和 citations 生成；
- `analysis_log.json` 记录被合并、跳过、延后处理的 section 决策；
- document package 的对外结构保持兼容。

## 2. merge 语义调整

原执行文档中把 `merge` 和 `log_only` 都直接排除出 `report.md`。这个实现方向短期可行，但需要把语义写清楚。

建议本阶段定义为：

```text
include   -> 进入 report.md，成为独立 H2 section
merge     -> 本阶段延后合并，不进入 report.md，但必须进入 analysis_log.json
log_only  -> 只进入 analysis_log.json
```

这样不会让读者看到弱证据段落，也不会让系统丢掉“未来值得合并”的信息。

后续可以给 `QualityGateDecision` 增加可选字段：

```python
QualityGateDecision(
    section_key="channel_reality",
    action="merge",
    target_section_key="business_model",
    reason="证据足以支撑局部观察，但不足以独立成节。",
)
```

等拼接层成熟后，再把 `merge` 内容自然并入目标 section，而不是单独堆成模块。

## 3. fallback 文案调整

fallback 不应写成“缺少证据，请查看日志”这种系统报错感文本。它应该更像一个正式产物状态说明，并且不包含公司事实判断。

建议 fallback：

```text
# {company_name}招股书长篇阅读

本次材料未形成满足证据阈值的正式解读正文。系统已保留处理记录，用于后续补充证据和优化生成策略。
```

该文案不包含事实性公司判断，也不包含 citation-shaped token，因此不需要 citation。

## 4. 拼接层输出结构

当至少一个 draft 通过质量门时，输出结构建议为：

```text
# {company_name}招股书长篇阅读

本文基于招股说明书中已抽取的可引用证据，围绕业务定位、能力配置、商业化验证和风险约束展开阅读。

## {draft.title}

{draft.body}
```

这段导语是方法说明，不是公司事实判断，因此不需要 citation。它能让报告不像一组生硬模块直接拼起来。

拼接层本阶段只做确定性处理：

- 按 draft 顺序输出，不按 decision 顺序输出；
- 只输出 `action == "include"` 的 draft；
- 跳过空 body 或只有空白的 body；
- 不改写 draft.body；
- 不重排 citation；
- 清理重复空行；
- 返回以换行结尾的 Markdown。

## 5. decision lookup 规则

拼接层可以构造 `section_key -> decision` 查找表，但最终顺序必须由 drafts 决定。

建议规则：

1. 遍历 drafts；
2. 用 `draft.section_key` 找 matching decision；
3. 没有 decision 的 draft 不进入 report；
4. `decision.action == "include"` 才进入 report；
5. 多余的 decision 不影响最终 report；
6. `merge` 与 `log_only` 不作为独立 section 输出。

需要补测试：

- draft 没有 matching decision 时不进入报告；
- decision 顺序和 draft 顺序不一致时，最终按 draft 顺序；
- 多余 decision 不影响输出。

## 6. citation 安全

拼接层不负责生成、重排或改写 citation。citation 仍由：

```text
evidence_packet.items -> citation_layer.py
```

负责。

但拼接层或 pipeline 至少要做轻量校验：最终 `report.md` 中出现的 `[C-xxx]` 必须都能在 `citation.json` 中找到。

建议接口预留可选参数：

```python
def assemble_report(
    company_name: str,
    drafts: list[SectionDraft],
    decisions: list[QualityGateDecision],
    valid_citation_ids: set[str] | None = None,
) -> str:
    ...
```

当 `valid_citation_ids` 不为空时，拼接层只做校验：

- 提取 included draft.body 中的 `[C-xxx]`；
- 检查每个 id 是否存在；
- 发现未知 citation id 时抛出确定性错误。

这样 citation 的所有权仍在 evidence/citation 层，但最终报告不会带着无效 citation 出包。

## 7. pipeline 集成

`_write_report_artifacts()` 应该在同一个上下文中生成 drafts、quality decisions、analysis log 和 report，避免重复跑 quality gate 导致状态不一致。

建议结构：

```python
section_drafts = generate_section_drafts(packet, report_inputs)
quality_decisions = apply_quality_gate(section_drafts, _evidence_policies(report_inputs))
analysis_log = build_analysis_log(packet.doc_id, quality_decisions)
citations = build_citations(packet)
valid_citation_ids = {citation.citation_id for citation in citations}
report = assemble_report(
    manifest.company_name,
    section_drafts,
    quality_decisions,
    valid_citation_ids=valid_citation_ids,
)
```

`analysis_log.json` 和 `report.md` 必须来自同一批 `quality_decisions`。

## 8. analysis_log.json 责任

最终 report 不展示弱证据占位、不展示“这里缺东西”的提示。相关信息进入 `analysis_log.json`。

建议日志至少保留：

```json
{
  "section_key": "channel_reality",
  "title": "渠道与商业化验证",
  "action": "merge",
  "reason": "证据足以支撑局部观察，但不足以独立成段。",
  "evidence_count": 2,
  "min_fact_count": 3,
  "strength": "medium",
  "required_strength": "high",
  "suggested_next_steps": [
    "补充主要平台销售额",
    "补充线上渠道拆分",
    "补充销售费用投放结构"
  ]
}
```

日志服务后续优化，不污染最终正文。

## 9. 测试补充

拼接层测试建议包含：

- 只包含 `include` decisions；
- 排除 `merge` 与 `log_only`；
- 按 draft 顺序输出；
- draft 没有 matching decision 时不输出；
- 多余 decision 不影响输出；
- 空 body 不输出；
- citation id 原样保留；
- fallback 不包含 `[C-xxx]`；
- 提供 `valid_citation_ids` 时，未知 citation id 会失败。

pipeline 测试建议包含：

- `run_one()` 输出 stitched report，且包含来自 `report_inputs` 的 section title；
- 被弱化策略挡下的 section 不出现在 `report.md`，但出现在 `analysis_log.json`；
- `merge` 和 `log_only` 出现在 `analysis_log.json`，但不作为独立 section 出现在 `report.md`；
- `reader_bundle.json` 来自 stitched report sections；
- `citation.json` 仍从 `C-001` 开始，并来自 `evidence_packet`；
- `report.md` 中的所有 `[C-xxx]` 都能在 `citation.json` 找到；
- pipeline 不再使用 legacy 固定长文作为 package report 来源。

验证命令：

```powershell
python -m pytest -q
git diff --check
git status --short
```

## 10. 验收标准

- 拼接模块存在并有 focused tests；
- 拼接函数只接收 `include` decisions，并使用 draft order；
- `merge` 本阶段作为 deferred merge 进入 `analysis_log.json`，不作为独立 report section；
- `merge` 与 `log_only` 继续记录在 `analysis_log.json`；
- 缺失 decision 的 draft 和空 body 不进入 `report.md`；
- fallback report 不包含 citation-shaped token；
- `_write_report_artifacts()` 使用 `section_drafts + quality_decisions + 拼接函数` 生成 `report.md`；
- `analysis_log.json` 和 `report.md` 来自同一批 quality decisions；
- `citation.json` 仍从 `evidence_packet` 生成；
- stitched report 中的 citation tokens 都能被 `citation.json` 覆盖；
- `reader_bundle.json` 基于 stitched report 构建；
- 全量测试通过。
