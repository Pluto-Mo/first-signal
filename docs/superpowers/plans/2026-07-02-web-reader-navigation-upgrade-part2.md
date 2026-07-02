### Step 5: Update Styles

修改 `web/src/styles.css`，添加新组件样式：

```css
/* Grouping Tabs */
.grouping-tabs {
  display: flex;
  gap: 0;
  padding: 16px 16px 0;
  border-bottom: 1px solid #E7E1D7;
  margin-bottom: 8px;
}

.grouping-tab {
  flex: 1;
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 14px;
  font-weight: 500;
  color: #5C635D;
  cursor: pointer;
  transition: all 0.2s;
}

.grouping-tab:hover {
  color: #1F2421;
  background: #F7F4EF;
}

.grouping-tab.is-active {
  color: #C4612F;
  border-bottom-color: #C4612F;
}

/* Document Tree */
.document-tree {
  padding: 8px 0;
  overflow-y: auto;
  max-height: calc(100vh - 180px);
}

.tree-group {
  margin-bottom: 4px;
}

.tree-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 16px;
  background: transparent;
  border: none;
  font-size: 14px;
  font-weight: 500;
  color: #1F2421;
  cursor: pointer;
  transition: background 0.2s;
}

.tree-group-header:hover {
  background: #F7F4EF;
}

.tree-group-icon {
  font-size: 16px;
}

.tree-group-label {
  flex: 1;
  text-align: left;
}

.tree-group-count {
  font-size: 12px;
  color: #5C635D;
}

.tree-group-items {
  padding-left: 24px;
}

.tree-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-left: 2px solid transparent;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.tree-item:hover {
  background: #F7F4EF;
  border-left-color: #E7E1D7;
}

.tree-item.is-selected {
  background: #F2E3D6;
  border-left-color: #C4612F;
}

.tree-item-name {
  font-size: 13px;
  font-weight: 500;
  color: #1F2421;
}

.tree-item.is-selected .tree-item-name {
  color: #C4612F;
}

.tree-item-date {
  font-size: 11px;
  color: #5C635D;
}

/* Sidebar */
.sidebar {
  width: 280px;
  min-width: 280px;
  background: #FBF9F5;
  border-right: 1px solid #E7E1D7;
  display: flex;
  flex-direction: column;
}

/* Workspace Layout */
.workspace {
  display: flex;
  gap: 0;
  min-height: calc(100vh - 120px);
}

.main-column {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

/* Header Update */
.app-header {
  padding: 24px 32px;
  border-bottom: 1px solid #E7E1D7;
  background: #FBF9F5;
}

.app-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1F2421;
  margin: 0;
}

/* Remove old styles */
.app-subtitle,
.eyebrow {
  display: none;  /* 删除冗余文案 */
}
```

### Step 6: Update docs_index.json Generation

需要在生成 `docs_index.json` 时添加 `industry` 字段。

修改 `src/ipo_evidence/pipeline.py` 或相关的索引生成代码，添加行业推断逻辑。

完整代码见 PR 文档第一部分。

### Step 7: Test Locally

```bash
# 1. 重新生成 docs_index.json（包含 industry 字段）
python -m ipo_evidence.cli generate-docs-index

# 2. 启动 Web 开发服务器
cd web
npm run dev

# 3. 打开浏览器访问 http://localhost:5173
```

**Expected Behavior:**
- ✅ 左侧显示树形目录
- ✅ 顶部有"按时间"和"按行业"两个 Tab
- ✅ 默认显示"按时间"分组（最近三天、本周、更早）
- ✅ 切换到"按行业"显示行业分组
- ✅ 点击文档可以切换阅读内容
- ✅ 标题显示"IPO 招股书研报"
- ✅ 没有冗余的说明文字

---

## 使用方式

**给 Codex 的指令：**

```
请按照 docs/superpowers/plans/2026-07-02-web-reader-navigation-upgrade.md 这个 PR 执行。

核心改动：
1. 创建 DocumentTree.tsx 和 GroupingTabs.tsx 组件
2. 创建 grouping.ts 工具函数（时间分类 + 行业分类）
3. 修改 App.tsx 使用新组件
4. 添加 CSS 样式
5. 标题改为"IPO 招股书研报"

完成后测试：
cd web
npm run dev
```
