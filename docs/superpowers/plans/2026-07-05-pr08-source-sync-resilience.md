# PR-08 source_sync 中断安全 + 配置真实化

分支名：`fix/source-sync-resilience`　规模：大　依赖：无（独立模块，可与 PR-03~07 并行）
背景：review 发现 #11、#12、#16、#17 及 source_sync 相关低优先级项（`docs/2026-07-05-full-project-review.md`）。核心底线：不让任何不完整或非 PDF 的文件顶着正式文件名进入 inbox；不让任何一次失败抹掉留档。

## 改动清单

### A. 中断安全（发现 #11）

1. **留档前置**：`service.run_sync` 拆为两步——`discover_and_filter()` 返回候选与过滤结果；cli 先落盘 discovery_log / filter_log，然后才进入下载阶段。任何下载失败都不再丢失发现与过滤留档。
2. **逐候选失败隔离**（`service.py:51-55`）：下载循环 per-candidate try/except，失败生成 `download_status="failed"` + 原因的记录，继续下一个；全部结果进 download_log。
3. **state 增量保存**（`cli.py:48-89`）：每成功下载一个即把 announcement_id 加入 processed_ids 并保存 state（io.py 的原子写在 PR-06 已就位；若本 PR 先执行，state 写入在本 PR 内改为临时文件 + os.replace）。
4. **state 损坏恢复**（`state.py`）：load 遇到非法 JSON → 把坏文件改名为 `.corrupt` 备份，按空 state 重建并打印 warning（配合 B-3 的文件存在检查，重建的代价只是窗口内的重复检查，不会覆盖已有文件）。

### B. 下载完整性（发现 #12）

1. **请求头**：PDF 下载复用 client 配置的 UA/Referer（当前用 python-requests 默认 UA，最易被风控）。
2. **内容校验**：落盘前校验响应 Content-Type 与文件魔数（前 5 字节 `%PDF-`）；不符 → `download_status="failed"` 留档，不写 inbox（对方返回 200 的 HTML 验证页是现实场景）。
3. **原子流式写入**：`stream=True` 分块写 `<name>.pdf.part`，完成并校验后 `os.replace` 改名；解决"半个 PDF 顶着正式文件名"与数百 MB 全量进内存两个问题。
4. **不覆盖已有文件**：目标文件已存在 → 记 `skipped` 并回填 state，不覆盖（当前 state 丢失后会静默重下覆盖）。

### C. HTTP 健壮性（发现 M1）

1. `client.py` 改用 `requests.Session` + `urllib3.util.retry.Retry`（total=3、指数退避、status_forcelist=[429,500,502,503,504]、尊重 Retry-After）。
2. `response.json()` 解析失败 → 抛带上下文的 RuntimeError（"响应非 JSON，可能被风控"）；`announcementId`/`adjunctUrl` 等关键字段改 `.get` + 缺失跳过并记 warning（`client.py:116,128` 当前裸索引）。
3. `SECNAME` 为空的 pool 记录直接 `continue`（当前会把别家公司的行业元数据挂到候选上，`client.py:135-147`）。
4. pool 遍历数量上限设为 `limit * 3`，避免 limit=3 却发约 40 个请求。

### D. 配置真实化（发现 #15-17）

1. `--days/--limit` 的 argparse 默认值从 `source_sync.yaml` 的 window/limits 读取（当前 yaml 这些键无人读，真实默认硬编码在 cli.py:26-27）；`max_downloads` 生效。
2. 节流加抖动：`request_interval_seconds + random.uniform(0, jitter_seconds)`（当前精确 2.0s 固定节奏比带抖动更像机器人）。
3. 标题排除词单一来源：删除 `client.py:14-26` 硬编码 `DEFAULT_BODY_EXCLUDED_TERMS`，由 cli 从 `filter_rules.yaml` 的 `body_title_exclude` 注入 client；被排除的公告也要进 filter_log 留档（当前零留档）。
4. `filter_rules.yaml` 的 `action` 字段不参与决策——删除该字段，filter_log 记录中区分 `filtered`/`observed` 状态（observed 项实际已下载，当前 `restorable: True` 的标注有误导）。
5. **留档迁址**：discovery/filter/download 日志从 `data/tmp/source_sync/`（按约定可清理，清理后被过滤样本彻底不可回捞）迁到 `runs/logs/source_sync/`；`sync_state.json` 留在 data/tmp（可重建缓存）。同步更新 `source_sync.yaml` 路径与 AGENTS.md 文件生命周期说明。
6. 运行结束打印 `discovered/filtered/downloaded/failed/skipped` 计数；pool 返回 0 条时打印明确 warning（与"没有新 IPO"可区分）。

### E. 测试（当前 client.py 零测试，恰是最脆弱模块）

- 用 requests-mock 或手写 mock 覆盖：client 关键字段缺失容错、非 JSON 响应、SECNAME 空跳过；downloader 非 PDF 响应不落 inbox、`.part` 原子改名、已存在跳过；下载中途失败时 discovery/filter 留档完好；state 损坏恢复。

## 验收标准

- 模拟第 2 个候选下载抛异常：第 1、3 个正常，三份日志齐全，state 含成功者。
- 模拟返回 HTML 的 200 响应：inbox 无新文件，download_log 有 failed 记录。
- 全量 pytest 通过。

## 验证

```bash
python -m pytest -q
python -m ipo_evidence.source_sync.cli sync-a-share --help
```
