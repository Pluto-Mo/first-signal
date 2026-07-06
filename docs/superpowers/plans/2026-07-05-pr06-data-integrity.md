# PR-06 数据完整性：防覆盖、人工字段保留、原子写、失败隔离

分支名：`fix/data-integrity`　规模：中　依赖：无
背景：review 发现 #6、#10、#18、L2（`docs/2026-07-05-full-project-review.md`）。重跑一次 run 会静默覆盖旧证据包和所有人工修正；全项目 JSON 写入非原子，中断留半截文件。

## 改动清单

1. **内容 hash 防覆盖**（`src/ipo_evidence/ingest.py` + `pipeline.py`）：
   - manifest 新增 `content_sha256` 字段（文件字节 sha256 的前 16 位 hex）。**不要改 doc_id 算法**——现有 6 个 data/docs 目录的 ID 必须保持兼容。
   - `run_one`：目标文档包已存在且已有 manifest 的 content_sha256 与当前 PDF 不一致 → 抛错，提示"同名文件内容不同，请改名或使用 --force"；cli `run` 加 `--force` 开关允许覆盖。
2. **run_one 保留人工字段**（`pipeline.py:113-120`）：重建 manifest 前读取已有 manifest，保留 `company_name`、`tags`、`source_url` 等人工可编辑字段（对齐 `scan_inbox`/`ingest.py:43-45` 已有的保留行为）；report_inputs 不再整体覆盖，复用 `_refresh_report_inputs` 的合并逻辑（保留手工 evidence_policy/evidence_refs 编辑）。
3. **批处理失败隔离**（`cli.py:70-72`）：run 循环逐 PDF try/except；失败时尽力写入 `parse_status="failed"` + 原因的 manifest，继续下一个；结束打印成功/失败汇总，有失败时 exit code 非 0。
4. **原子写**（`src/ipo_evidence/io.py:15-34`）：`write_text`/`write_json` 改为写临时文件（同目录、随机后缀）后 `os.replace` 到目标路径（Windows 下同样原子）。该改动自动惠及 manifest、evidence_packet、source_sync 的 state 等所有调用方。
5. **regenerate_report 顺序修正**（`pipeline.py:180-182`）：当前先写 manifest="reported" 再生成工件，失败后 manifest 与工件不同步。改为：全部产物先在内存生成 → 逐一落盘 → 最后才更新 manifest 状态；生成中途失败时 manifest 保持原状态。
6. **web_index 双写去重**（`pipeline.py:105` 与 `:152` 各写一次）：删一处。

## 验收标准

- 新增测试：同名不同内容的 PDF 第二次 run → 报错且旧包未被修改；`--force` 后覆盖成功且 content_sha256 更新。
- 新增测试：run_one 重跑保留 manifest 人工字段与 report_inputs 手工编辑。
- 新增测试：3 个 PDF 中第 2 个抛异常 → 第 1、3 个正常完成，退出码非 0。
- 新增测试：write_json 目标已存在时中断（mock os.replace 前抛错）→ 原文件内容完好。
- 全量 pytest 通过。

## 验证

```bash
python -m pytest -q
```
