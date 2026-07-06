# PR-02 llm_caller 安全加固与异常覆盖

分支名：`fix/llm-caller-hardening`　规模：小　依赖：无
背景：review 发现 #13、#14、卫生项（`docs/2026-07-05-full-project-review.md`）。招股书是外部输入，经 prompt 进入 agent 子进程；当前 agent 以仓库根为工作区（可读 .env），且环境变量未过滤（cli.py:83 的 load_dotenv 已把 PADDLEOCR_API_TOKEN 注入环境）——提示注入可诱导 agent 把 token 写进报告输出，而报告会发布到 gh-pages。

## 改动清单（全部在 `src/ipo_evidence/llm_caller.py`，另有调用方跟随修改）

1. **受限工作区**：`call_agent_for_narrative` 的默认 workspace 不再是 `repo_root()`，改为 `data/tmp/agent_workspace/`（不存在则创建的空目录）。prompt 经 stdin 传入，agent 不需要读仓库。
2. **环境变量过滤**：`subprocess.run(..., env=filtered_env)`，filtered_env 从 `os.environ` 复制后剔除名字匹配 `TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL`（不区分大小写）的变量。保留 PATH、HOME/USERPROFILE、APPDATA 等 codex CLI 运行所需变量。
3. **异常覆盖**：`subprocess.run` 外层 try/except 捕获 `OSError`（含 FileNotFoundError/PermissionError），包装为 `RuntimeError("Agent CLI not available: ...")` 抛出——这样上游 skill_executor / narrative_engine 现有的 except 即可全覆盖并走 fallback。同时给 `subprocess.run` 加 `errors="replace"` 防 UnicodeDecodeError。
4. **临时文件清理**：`NamedTemporaryFile(delete=False)` 创建的 output_path 在 finally 中 `unlink(missing_ok=True)`。
5. **max_tokens 诚实化**：签名中删除 `max_tokens` 参数（当前 `del max_tokens` 是假接口），更新所有调用方（skill_executor.py、narrative_engine.py）与 `tests/test_llm_caller.py:82` 附近的假断言；长度约束保留在 prompt 文本中。
6. **改名**：`call_claude_for_skill` → `call_llm_for_skill`（实际后端是 codex，名字误导），更新全部调用方与测试。
7. **输出防泄漏**：新增小函数 `redact_env_secrets(text)`——对输出文本扫描当前进程中已知敏感 env 值（步骤 2 剔除清单命中的变量的值，长度 ≥ 8 才比对），命中则替换为 `[REDACTED]`；在 `call_agent_for_narrative` 返回前调用。

## 验收标准

- 新增测试：codex 命令不存在时（mock subprocess.run 抛 FileNotFoundError）`call_agent_for_narrative` 抛 RuntimeError 而非 FileNotFoundError。
- 新增测试：env 过滤后子进程 env 中无 `PADDLEOCR_API_TOKEN`。
- 新增测试：输出中包含已知 token 值时被替换为 `[REDACTED]`。
- 全量 pytest 通过；`grep -rn "call_claude_for_skill" src tests` 无结果。

## 验证

```bash
python -m pytest -q
grep -rn "max_tokens" src/ipo_evidence/llm_caller.py
```
