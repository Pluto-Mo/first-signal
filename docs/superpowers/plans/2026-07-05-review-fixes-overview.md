# 2026-07-05 Review 修复总览（PR 拆分）

来源：`docs/2026-07-05-full-project-review.md`（26 条编号发现）。本目录下 `2026-07-05-pr01` ~ `pr10` 共 10 个 PR 规格文件，每个可独立交给 Codex 执行。

## PR 清单与执行顺序

| 顺序 | PR | 分支名 | 规模 | 依赖 | 主题 |
|---|---|---|---|---|---|
| 1 | pr01 | `fix/docs-alignment` | 小 | 无 | 文档对齐 + 仓库卫生（先做：让 Codex 拿到正确的 AGENTS.md 地图） |
| 2 | pr02 | `fix/llm-caller-hardening` | 小 | 无 | llm_caller 安全加固（注入泄密路径、异常覆盖） |
| 3 | pr03 | `fix/citation-enforcement` | 中 | 无 | citation 代码级强制校验 |
| 4 | pr04 | `fix/parser-honesty` | 中 | 无 | 解析层去伪（stub 显式化、标题正则、页码假设） |
| 5 | pr05 | `fix/table-evidence-honesty` | 中 | 无 | 表格证据诚实化 |
| 6 | pr06 | `fix/data-integrity` | 中 | 无 | doc_id 防覆盖、人工字段保留、原子写、失败隔离 |
| 7 | pr07 | `fix/quality-truthfulness` | 大 | pr03 | 质量状态真实化 + quality gate 接线 |
| 8 | pr08 | `fix/source-sync-resilience` | 大 | 无 | source_sync 中断安全 + 配置真实化（独立模块，可与 3-7 并行） |
| 9 | pr09 | `chore/dead-code-cleanup` | 大 | pr03, pr07 | 死代码大清扫（约减三分之一代码量） |
| 10 | pr10 | `fix/web-reader-and-ci` | 中 | 无 | 前端修复 + bundle 瘦身 + CI 加测试（可随时并行） |

## 使用方式

每次给 Codex 的提示词模板：

```text
阅读并完整执行 docs/superpowers/plans/2026-07-05-pr0X-<name>.md。
遵守 AGENTS.md 约定。不要超出该文件列出的改动范围。
完成后运行文末验证命令，报告全部结果（包括失败）。
```

## 规则

- 一次只开一个 PR，合并进 main 后再开下一个（pr08、pr10 例外，可并行——它们与其他 PR 无共同文件）。
- pr01/pr09/pr10 含文件删除，删除清单已在规格中逐一列明；把规格交给 Codex 即视为对清单内删除的批准，清单外一律不得删。
- 任何 PR 不得触碰 `data/inbox/`、`data/docs/`、`.env`。
- 每个 PR 的验收标准若无法全部满足，Codex 应停下说明，而不是放宽标准。

## 后续路线（修完之后）

- 阶段 2a（当前）：完成上述 10 个 PR → 得到"可信的单文档闭环"。
- 阶段 2b：泛化验证——用 data/inbox 现有 6 家不同行业公司做泛化测试集，全部跑通并人工抽查 citation；建立 `runs/evals/` 评测基线（citation 命中率、页码准确率、fallback 率、每份报告成本）；每周真实使用（sync → 读报告 → 标注错误）。
- 阶段 3：才是港股兼容、多公司对比、新增 skills。
