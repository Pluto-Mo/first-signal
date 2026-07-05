# PR-10 前端修复 + bundle 瘦身 + CI 加测试

分支名：`fix/web-reader-and-ci`　规模：中　依赖：无（可随时并行）
背景：review 发现 #19、#20、#21 及前端低优先级项（`docs/2026-07-05-full-project-review.md`）。前端 XSS 已确认干净，无需处理。

## 改动清单

### A. App 状态机（发现 #20）

1. `web/src/App.tsx:83-90`：`setBundlesById` 移出 `isActive` 守卫（缓存按 doc_id 键入，永不过期，写缓存无需守卫）——已下载的 bundle 不再被丢弃，切回文档不再整包重下；`setError`/`setIsBundleLoading` 保留守卫。顺带消除"A 加载中切到已缓存 B 时 isBundleLoading 卡 true"的问题。
2. 错误状态按 doc_id 记录（或切换文档时统一清 error），错误横幅不再挂在别的文档上；错误时渲染"重试"按钮，通过 `retryToken` state 加入 effect 依赖强制重跑加载（当前点同一文档因 React bail-out 永远无法重试）。
3. 删除死代码：`App.tsx:124-131` 两分支相同的冗余 effect、`:162` 无样式规则的 `has-drawer` class、无人引用的 `web/src/components/DocumentList.tsx`（删除已获批准）。

### B. 健壮性

4. `web/src/lib/api.ts:17`：`as T` 纯断言改为最小运行时校验（手写十几行，不引 zod）——如 `Array.isArray(data.sections)`，不符合抛带 doc_id 的可读错误走现有 error UI。
5. `web/src/main.tsx`：包一层 ErrorBoundary 兜底，坏数据不再白屏。
6. `web/src/components/CitationDrawer.tsx`：加 Esc 关闭（keydown 监听）；可选：打开时聚焦抽屉、关闭归还焦点。
7. `web/src/lib/types.ts:50`：`title?: string` 改 `title?: string | null`（实测 JSON 为 null）。
8. `web/src/lib/grouping.ts:145-158`：删除行业推断（`/智能|AI/i` 会把"龙鑫智能装备"归为人工智能，且硬编码公司名）——行业只信 index.json 的 `industry` 字段，无则"未分类"。同步手工修正 `web/showcase-data/index.json` 中已知错误的行业标注。

### C. bundle 瘦身（发现 #19）

9. `src/ipo_evidence/reader_bundle.py`：citations 只输出被 sections 实际引用的条目（完整清单仍在 citation.json）。实测 97% 的 citation 从未被引用，单文档 bundle 最大 1.9MB 近半是死重。
10. 一次性迁移：写脚本（或就地用 Python）把 `web/showcase-data/*/reader_bundle.json` 按同一规则过滤重写（保留 index.json 与目录结构），预期 showcase-data 从 7.5MB 降到约 3-4MB。

### D. 测试与 CI（发现 #21）

11. `web/src/__tests__/`：删除 129-131、148-150 行"旧 UI 文案不存在"的否定断言（删功能残留）；新增：fetch 404 → 错误 UI → 点重试恢复；切换文档后切回不再发起第二次 fetch（mock fetch 计数）。
12. `.github/workflows/pages.yml`：build 前加测试步骤（web 下 `npm test`）；`on.push` 加 `paths: ["web/**", ".github/workflows/pages.yml"]`。
13. 新增 `.github/workflows/tests.yml`：push/PR 触发，跑 `python -m pytest -q`（安装 `pip install -e .[dev]`）+ web vitest。
14. `web/package.json:9` 的 `--base /first-signal/` 旁加注释说明与仓库名耦合（或在 CI 用 `--base /${{ github.event.repository.name }}/` 传入）。
15. 可选：删除 `web/vite.config.ts:23-74` 自写静态中间件（Vite publicDir 本就 serve 这些 JSON）；删除前用 dev server 验证中文路径 JSON 仍可访问，不行就保留。

## 验收标准

- `npm test` 全过（含新增用例）；`npm run build` 与 `npm run build:pages` 成功。
- showcase-data 总体积 ≤ 4.5MB 且 Demo 功能不变（本地 `npm run dev` 抽查两个文档的 citation 抽屉）。
- workflows YAML 语法有效（`gh workflow` 或 actionlint 校验，没有就目检）。

## 验证

```bash
cd web && npm test && npm run build
du -sh web/showcase-data
python -m pytest -q
```
