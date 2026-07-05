# PR-05 表格证据诚实化

分支名：`fix/table-evidence-honesty`　规模：中　依赖：无
背景：review 发现 #8（`docs/2026-07-05-full-project-review.md`）。表格 citation 目前会伪造定位（硬编码章节与页码）并合成原表不存在的"合计"伪事实——对"判断必须可追溯"的项目，伪造定位比缺失定位更糟。

## 改动清单

1. **章节不伪造**：`src/ipo_evidence/pipeline.py:130` 把 parser raw_tables 的 section_path 硬编码为 `["业务和技术"]`——改为项目既有的 `["未识别章节"]` 约定（除非 parser 真实返回了章节信息）。
2. **页码不伪造**：`src/ipo_evidence/table_extractor.py:17-26` 缺失/非法页码静默置 1——改为允许 `page_number=None`（同步调整 models.py 相应字段为 Optional），页码缺失的表格证据 quality_score 降档，reader_bundle/citation 展示侧显示"页码缺失"而不是"第 1 页"。
3. **删除跨行求和合成**（`src/ipo_evidence/evidence.py:316-456` `_append_table_summary_items`）：对全数值列一律求和会产出"毛利率合计150%""年份合计6069"这类原表不存在的伪证据。整体删除合计合成，保留每行事实（row facts）条目；同步删除对应测试断言。
4. **丢弃与截断可见化**：`evidence.py:117`（rowspan/colspan 表格直接跳过）与 `:165`（行数截断至 12）——跳过与截断时计数，写入 parse_report（如 `tables_skipped_merged_cells`、`table_rows_truncated`），并在 analysis_log 留一条说明。不改变跳过/截断行为本身。
5. **删除硬编码合成 claim**：`evidence.py:498-513` 命中"研发、生产和销售"即注入固定措辞合成条目（原文即使是否定句也会生成）——删除。

## 验收标准

- 新增测试：毛利率/占比/年份列不再产生"合计"证据条目。
- 新增测试：页码缺失的表格证据 page_number 为 None 且 quality_score 低于有页码的同等表格。
- 新增测试：含 rowspan 的表格被跳过时 parse_report 计数 +1。
- 现有 6 个文档包不需重新生成（本 PR 只改生成逻辑，不迁移旧数据）。
- 全量 pytest 通过。

## 验证

```bash
python -m pytest -q
```
