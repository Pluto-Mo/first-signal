# Report Generation Notes

这份文档说明当前长版 report 是怎样从 `evidence_packet.json` 和 `report_inputs.json` 生成的，以及当前写作 prompt 放在哪里。

## 入口文件

主要可调整文件：

- `configs/report_prompt.yaml`
  - 放当前 report 的写作规则、三个视角、focus points、约束和 evidence 选择规则。
  - 后续想调文章方向，优先改这里。
- `src/ipo_evidence/report_inputs.py`
  - 读取 `configs/report_prompt.yaml` 里的 `input_views`。
  - 把 evidence 按三个视角组织成 `report_inputs.json`。
- `src/ipo_evidence/report_generator.py`
  - 读取 `evidence_packet.json` 和 `report_inputs.json`。
  - 生成最终 `report.md`。

生成链路：

```text
evidence_packet.json
  -> build_report_inputs()
  -> report_inputs.json
  -> generate_report(company_name, packet, report_inputs)
  -> report.md + citation.json + reader_bundle.json
```

## 阅读器输出进度

当前这条链路已经不止生成报告文本，还会顺手产出给 Web 阅读器直接消费的阅读资产：

- `reader_bundle.json`
  - 由 `src/ipo_evidence/reader_bundle.py` 生成。
  - 把 `report.md` 的章节和段落切成前端可直接渲染的 `sections -> blocks` 结构。
  - 把 `citation.json` 映射成阅读器可直接使用的 `citations` 列表，并补齐质量状态与最小定位字段。
- `web_index.json`
  - 由 `src/ipo_evidence/web_index.py` 生成。
  - 用于聚合每个文档包的列表信息，并暴露 `reader_bundle_path` 给前端按需加载。

当前 Web 阅读器已经切到真实文档包驱动，不再依赖硬编码 demo 数据；正文也已改成连续长文模式，citation 默认收起，点击后再以右侧抽屉方式展开。

## report_inputs 怎么被调用

`report_inputs.json` 当前不是直接保存正文，而是保存“怎么组织 evidence”的调度结构。

每个 `section_group` 代表一个阅读视角：

- `company_and_industry`：公司介绍与行业概况
- `personal_investment`：个人投资视角
- `cognitive_worldview`：认知世界的方式

每个 group 里最重要的是：

- `section_key`：生成器识别这个视角用的 key。
- `title`：最终 report 的一级标题来源。
- `focus_points`：这个视角应该关注什么。
- `constraints`：这个视角写作时不能越过的边界。
- `source_sections`：配置里定义，决定哪些 canonical section 的 evidence 会进入这个视角。
- `evidence_refs`：实际写入 `report_inputs.json` 的证据引用列表，只保存 evidence id、rank、role 和 label。

生成报告时，`report_generator.py` 会先用 `report_inputs.section_groups[].evidence_refs` 找对应 evidence。然后再用 `canonical_section` 补充同类 evidence，避免 input 不完整时文章断掉。

## 当前 prompt 放在哪里

当前 prompt 已落实到 `configs/report_prompt.yaml` 的 `writing_prompt`：

- `role`：作者角色。
- `objective`：最终产物目标。
- `style`：文风约束。
- `required_views`：三个必写视角。
- `citation_rule`：citation 编号和事实引用规则。
- `evidence_selection_rule`：证据选择规则。

现在的生成器不是直接调用大模型生成正文，而是用确定性模板生成。因此 `writing_prompt` 目前主要承担两件事：

- 让你能看到当前写作意图和约束。
- 作为后续接入 LLM prompt / skills 时的单一配置来源。

## 当前生成逻辑

最终 report 是弱结构化长文，固定为三段大视角：

1. 公司介绍与行业概况
2. 个人投资视角
3. 认知世界的方式

正文内部会根据关键词从 evidence 中选材料。例如：

- 产品和场景：优先选 `business_and_product`，并倾向 `text_quote`。
- 行业和产业链：优先选 `company_and_industry` 视角下的行业、市场规模、产业链 evidence。
- 财务和增长：优先选 `financials`。
- 募投：优先选 `use_of_proceeds`。
- 风险和治理：优先选 `risks`、`governance`、`related_party`。

citation 编号不重新排序，始终按 `evidence_packet.items` 的原始顺序生成。例如第一个 evidence 在报告里引用为 `[C-001]`。

## 后续怎么调整

如果只想调整文章方向，优先改 `configs/report_prompt.yaml`：

- 改标题：`report_title_suffix`
- 改三个视角标题：`input_views.*.title`
- 改每个视角关注点：`focus_points`
- 改每个视角纳入哪些 evidence：`source_sections`
- 改文风边界：`writing_prompt.style`

如果想调整具体段落怎么写，才需要改 `src/ipo_evidence/report_generator.py`。

如果后续接入真正的 LLM 生成，建议仍保留现在的结构：`report_inputs.json` 负责调度证据，`configs/report_prompt.yaml` 负责写作规则，`report_generator.py` 只负责把两者组合成 report。
