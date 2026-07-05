# PR-01 文档对齐 + 仓库卫生

分支名：`fix/docs-alignment`　规模：小　依赖：无
背景：review 发现 #23-26 及仓库卫生项（`docs/2026-07-05-full-project-review.md`）。文档与实现脱节，且 Codex 每个会话都会读 AGENTS.md，必须先给它正确的地图。

## 改动清单

1. **AGENTS.md「目录约定」**：改为实际结构——`src/ipo_evidence/` 平铺模块 + `parser/`、`source_sync/` 子包；web 为 `web/src/components|lib`、`web/showcase-data/`；configs 按现存文件列出。
2. **AGENTS.md「验证约定」**：替换全部失效命令为实际命令：
   - `python -m pytest -q`
   - `python -m ipo_evidence.cli scan-inbox`
   - `python -m ipo_evidence.cli run --limit 3`
   - `python -m ipo_evidence.cli generate-report --doc-id <doc_id>`
   - `python -m ipo_evidence.source_sync.cli sync-a-share --days 7 --limit 3`
   - web: `npm run dev` / `npm run build` / `npm test`（在 web/ 下）
3. **README.md「快速开始」**：`python -m ipo_evidence.cli sync-a-share` 改为 `python -m ipo_evidence.source_sync.cli sync-a-share`；`build-web-index` 子命令不存在——删除该条，并注明 web_index.json 随 run / generate-report 自动生成。
4. **README.md「核心技术栈」**：LLM 集成描述改为事实：当前通过本地 agent CLI（codex exec 子进程）调用，接口抽象在 `llm_caller.py`，可替换为 Anthropic API。
5. **删除重复 README**（已获批准）：先 `diff README.md README.github.md`，若 README.github.md 有值得保留的差异行先合并回 README.md；然后删除 `README.github.md` 和 `docs/README-new.md`（两者内容完全相同）。
6. **.gitignore**：加一行 `.tmp/`。
7. **根 package.json**：加 `"private": true`。

## 验收标准

- AGENTS.md 中每条验证命令均实际可运行（scan-inbox/run 可只验证命令能被 argparse 识别，如 `--help`）。
- README 快速开始中每条命令 `--help` 均不报"invalid choice"。
- 仓库中只剩一份 README。

## 验证

```bash
python -m pytest -q
python -m ipo_evidence.cli --help
python -m ipo_evidence.source_sync.cli --help
git status --short
```
