# PR-04 解析层去伪：stub 显式化、标题正则、页码假设

分支名：`fix/parser-honesty`　规模：中　依赖：无
背景：review 发现 #4、#7、#9、L8（`docs/2026-07-05-full-project-review.md`）。

## 改动清单

### A. stub 降级必须显式 opt-in（发现 #4）

1. `src/ipo_evidence/parser/__init__.py:18-20`：删除"缺 token 且有 fixture 就静默用 ApiStubParser"的分支。缺 token 一律抛 RuntimeError（保留现有报错文案）。
2. `src/ipo_evidence/cli.py`：`run` 子命令加 `--use-stub` 开关。未加时 `handle_run` 不再传 fixture（传 None），provider 为 paddleocr_vl 且缺 token → 明确报错退出；加 `--use-stub` 时才使用 `tests/fixtures/sample_prospectus.txt`，并在 stdout 打印醒目提示 `WARNING: using stub parser, output is sample data`。
3. `tests/test_parser_factory.py:33-46`：该测试目前把静默降级固化为预期行为，改为断言"缺 token 时抛 RuntimeError"；stub 路径测试改为显式传 provider=api_stub。

### B. 标题正则修复（发现 #7）

4. `src/ipo_evidence/section_mapper.py:21`：`_HEADING_PATTERNS` 中匹配数字开头的模式，要求编号后必须跟分隔符或空白（形如 `^(\d+(?:\.\d+)*)(?:[、.．]|\s+)(.+)$` 的语义），使 `"2023年，公司实现营业收入12,000万元。"`、`"5G通信模块是公司核心产品"` 不再被判为标题。
5. 负例回归测试（`tests/test_section_mapper.py`）：上述两句判定为正文；`"1、公司概况"`、`"1.2 主营业务"`、`"3 财务信息"` 仍判为标题。另在 `tests/test_evidence.py` 加一条：数字开头正文句子会进入证据包（当前被 `_is_heading_only` 静默排除）。

### C. 页码假设诚实化（发现 #9）

6. `src/ipo_evidence/parser/paddleocr_vl.py:92`：当前假设"JSONL 行号 = 页码"。检查 API 响应结构（可查 data/docs 现有包的 parser_raw 留档或 PaddleOCR VL 文档）是否含真实页码字段：有则改用；无法确认则保留行号推断，但在 parse_report 中记录 `page_number_source: "line_index"`（让假设可见），并新增多页 fixture 测试固定该行为。
7. `src/ipo_evidence/parser/paddleocr_vl.py:124-138`：公司名兜底会把首行任意文本（如"重要声明"）当公司名并在 pipeline.py:125 覆盖文件名推断。改为：兜底提取失败/不像公司名时返回空串，让 pipeline 的文件名推断兜底。

## 验收标准

- 缺 token + 不加 --use-stub：`run` 报错退出，不产出任何文档包。
- `--use-stub` 路径打印 WARNING 且功能与旧行为一致（现有 pipeline 测试仍过）。
- B 的全部正/负例测试通过。
- 全量 pytest 通过。

## 验证

```bash
python -m pytest -q
python -m ipo_evidence.cli run --help
```
