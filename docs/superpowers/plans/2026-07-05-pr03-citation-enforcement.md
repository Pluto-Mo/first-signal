# PR-03 citation 代码级强制校验

分支名：`fix/citation-enforcement`　规模：中　依赖：无
背景：review 发现 #1、卫生项 citation 正则（`docs/2026-07-05-full-project-review.md`）。这是项目立身之本："无来源不进报告"目前只有 prompt 约束，唯一的校验函数困在生产不可达的 report_assembler.py 里。LLM 输出 `[C-999]` 会原样进 report.md 和 reader_bundle.json。

## 改动清单

1. **提取共享校验**：把 `report_assembler.py:47` 的 `_validate_citations` 逻辑迁移到 `src/ipo_evidence/citation_layer.py`，公开为 `extract_citation_ids(text) -> set[str]` 和 `find_unknown_citations(text, valid_ids) -> set[str]`。report_assembler 暂时改为调用共享版（该模块将在 PR-09 删除，不必精修）。
2. **正则修复**：所有 citation 编号正则从 `C-\d{3}` 改为 `C-\d{3,}`（`report_assembler.py:9`、`reader_bundle.py:19` 及新共享模块），支持第 1000 条以上证据。
3. **叙事路径强制校验**（`narrative_engine.py`，generate_narrative 主流程）：LLM 返回后提取全部 citation 编号，与本次提供给 prompt 的合法 citation 集合求差集：
   - 有未知编号 → 构造纠正提示（列出非法编号，要求只使用给定编号）重试一次；
   - 重试后仍有 → 放弃 LLM 输出，走现有 fallback 路径（fallback 的 citation 由代码拼接，天然安全），并在 narrative_trace 中记录 `invalid_citations` 列表与 `citation_validation_failed=true`。
4. **reader_bundle 兜底**（`reader_bundle.py:98` 附近）：提取 citation_ids 后过滤掉 citation.json 中不存在的编号，被过滤数量记入 bundle 元信息（如 `dropped_citation_ids`），不静默。
5. **删除装饰性配置**（已获批准）：删除 `configs/prompts/citation_checker.yaml`（无任何代码加载，制造"有校验层"的假象）；同步删除 `tests/test_report_inputs.py:82,297` 附近仅断言该文件存在的测试。

## 验收标准

- 新增测试：mock LLM 首次返回含 `[C-999]` → 触发一次重试；重试仍非法 → 走 fallback 且 trace 记录非法编号。
- 新增测试：合法编号（含 4 位数如 `C-1000`）全部通过校验。
- 新增测试：reader_bundle 对不存在的编号过滤并记录数量。
- 全量 pytest 通过。

## 验证

```bash
python -m pytest -q
grep -rn "citation_checker" src tests configs
```
