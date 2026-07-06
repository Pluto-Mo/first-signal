# PR-09 死代码大清扫

分支名：`chore/dead-code-cleanup`　规模：大（纯删除 + 少量改写）　依赖：PR-03（citation 校验已迁出 report_assembler）、PR-07（gate 不再依赖草稿流水线）
背景：review 死代码清单（`docs/2026-07-05-full-project-review.md`）。多轮重构留下约三分之一死代码，是可维护性最大的负担。

**删除授权**：以下清单内的删除已获项目所有者批准；清单外任何文件不得删除。删除前逐项 `grep -rn` 确认生产代码（src/、web/src/）零引用——若发现引用，停下报告而不是强删。

## 删除清单

### Python 模块与代码块

1. `src/ipo_evidence/report_assembler.py` 整个文件 + `tests/test_report_assembler.py`（唯一价值 `_validate_citations` 已在 PR-03 迁出；pipeline 从不调用 assemble_report）。
2. `src/ipo_evidence/report_generator.py` 旧模板报告路径：`generate_report`、`_report_body`、`KEYWORDS`（含"比亚迪/华为/DUI中台"等思必驰样本词表）、`LOW_VALUE_SNIPPETS`、`SECTION_ORDER` 及仅被它们使用的辅助函数。**注意**：先 grep 确认 `build_citations` 等仍被 pipeline/reader_bundle 引用的符号，保留被引部分；对应删减 `tests/test_report_generator.py`、`tests/test_report_and_citation.py`（保留 citation 构建相关测试）。
3. `src/ipo_evidence/section_generator.py` + `src/ipo_evidence/section_writer.py` 整体 + `tests/test_section_generator.py` + `tests/test_section_writer.py`（PR-07 后 gate 不再依赖 drafts，正文早已由叙事引擎负责）。同时移除 pipeline.py 中对 `generate_section_drafts` 的调用与 import。
4. `src/ipo_evidence/narrative_engine.py` 的 `_build_debug_prompt`（零调用）。
5. `src/ipo_evidence/paths.py` 的 `doc_dir`（生产零调用，仅测试使用；删除函数与对应测试）。
6. `src/ipo_evidence/web_index.py:178-187` 硬编码"思必驰/永励"的行业推断：改为只读 manifest.tags（无则"未分类"），删除公司名规则。
7. `src/ipo_evidence/evidence.py` 与 `quality_gate.py` 之间的魔法字符串契约（`"对应数据为"`，evidence.py:301 / quality_gate.py:67）：抽成共享常量（顺手项）。

### 配置文件

8. `configs/section_mapper.yaml`（规则硬编码在 section_mapper.py 的 CANONICAL_RULES，yaml 无人读；以代码为单一来源，删 yaml）。
9. `configs/scoring_rules.yaml`：**若 PR-07 已接线则保留**；未接线才删。
10. `configs/prompts/stitch_writer.yaml` + `tests/test_report_inputs.py` 中对它的存在性断言（随 report_assembler 一起废弃）。
11. `configs/report_profiles/consumer_product.yaml`、`cyclical_industry.yaml`、`technology_company.yaml`（`default_report_profile_key` 恒返回 "base"，三个 profile 不可达）；同时删除 `report_profiles.select_report_profile`（仅测试调用）及对应测试；`base.yaml` 中无消费者的 `default_skill_refs` 键删除。
12. `configs/report_prompt.yaml` 的 `writing_prompt` 块（117-138 行，全仓零引用）——其中"没有来源定位的事实不得进入最终报告"这条纪律已由 PR-03 的代码校验承接。
13. `configs/report_prompt.yaml` / report_inputs 里的 `token_budget`、`focus_points`、`constraints`（只被原样复制、无消费方）：删除。
14. `configs/skills/*.yaml` 的 `output_schema` 块：无消费者且已与代码输出漂移（如 reader_value_translate 声明 for_tech_people 而代码产出 trend_*）。缩减 yaml 为 key/title/action。
15. `configs/parser.yaml` 中无人读取的键（`input_type`、`preserve_source_pdf`、`outputs`）。

### 其他

16. `src/ipo_evidence/skill_executor.py` fallback 中的端侧 AI 硬编码词表（"AI 芯片""智慧出行""车载"等产品/场景候选，316-321/377-383/404-409 行附近）：PR-07 已做诚实化标注，本 PR 把词表本身替换为"证据原句拼接"或删除（换任何非 AI 公司这些词表只产生噪声）。

## 验收标准

- 全量 pytest 通过（删除对应死测试后）。
- `python -m ipo_evidence.cli run --use-stub --limit 1` 冒烟通过（完整跑出一个文档包）。
- `grep -rn "assemble_report\|section_writer\|stitch_writer\|select_report_profile" src configs` 零结果。
- `git diff --stat` 呈净删除（预期删除量为四位数行级）。

## 验证

```bash
python -m pytest -q
python -m ipo_evidence.cli run --use-stub --limit 1
```
