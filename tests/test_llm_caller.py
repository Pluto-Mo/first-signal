import subprocess
from pathlib import Path

import pytest

from ipo_evidence.llm_caller import call_agent_for_narrative, call_llm_for_skill


def test_call_agent_for_narrative_invokes_codex_exec(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="ignored stdout", stderr="")

    monkeypatch.setattr("ipo_evidence.llm_caller.subprocess.run", fake_run)
    monkeypatch.setattr(
        "ipo_evidence.llm_caller._read_last_message",
        lambda _path: "这是一篇由自身 agent CLI 生成的报告。",
    )

    output = call_agent_for_narrative(
        user_prompt="请写报告",
        system_prompt="只输出正文",
        timeout=30,
    )

    cmd, kwargs = calls[0]
    command_name = Path(cmd[0]).name.lower()
    assert command_name.startswith("codex") or cmd[0].lower() == "powershell"
    assert "exec" in cmd
    assert "--sandbox" in cmd
    assert "read-only" in cmd
    assert kwargs["input"].startswith("只输出正文")
    assert output == "这是一篇由自身 agent CLI 生成的报告。"


def test_call_agent_for_narrative_raises_timeout(monkeypatch):
    def fake_run(_cmd, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="codex exec", timeout=1)

    monkeypatch.setattr("ipo_evidence.llm_caller.subprocess.run", fake_run)

    with pytest.raises(TimeoutError, match="Agent CLI timed out"):
        call_agent_for_narrative("prompt", "system", timeout=1)


def test_call_agent_for_narrative_raises_runtime_error(monkeypatch):
    def fake_run(cmd, **_kwargs):
        return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="boom")

    monkeypatch.setattr("ipo_evidence.llm_caller.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="Agent CLI failed"):
        call_agent_for_narrative("prompt", "system")


def test_call_agent_for_narrative_wraps_missing_agent_cli(monkeypatch):
    def fake_run(_cmd, **_kwargs):
        raise FileNotFoundError("codex not found")

    monkeypatch.setattr("ipo_evidence.llm_caller.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="Agent CLI not available"):
        call_agent_for_narrative("prompt", "system")


def test_call_agent_for_narrative_filters_sensitive_env(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="safe output", stderr="")

    monkeypatch.setenv("PADDLEOCR_API_TOKEN", "secret-token-value")
    monkeypatch.setenv("SAFE_RUNTIME_FLAG", "keep-me")
    monkeypatch.setattr("ipo_evidence.llm_caller.subprocess.run", fake_run)
    monkeypatch.setattr("ipo_evidence.llm_caller._read_last_message", lambda _path: "")

    call_agent_for_narrative("prompt", "system")

    child_env = captured["env"]
    assert "PADDLEOCR_API_TOKEN" not in child_env
    assert child_env["SAFE_RUNTIME_FLAG"] == "keep-me"


def test_call_agent_for_narrative_redacts_sensitive_env_values(monkeypatch):
    leaked_token = "secret-token-value"

    def fake_run(cmd, **_kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=f"token: {leaked_token}", stderr="")

    monkeypatch.setenv("PADDLEOCR_API_TOKEN", leaked_token)
    monkeypatch.setattr("ipo_evidence.llm_caller.subprocess.run", fake_run)
    monkeypatch.setattr("ipo_evidence.llm_caller._read_last_message", lambda _path: "")

    output = call_agent_for_narrative("prompt", "system")

    assert leaked_token not in output
    assert output == "token: [REDACTED]"


def test_call_llm_for_skill_reuses_agent_cli_wrapper(monkeypatch):
    captured = {}

    def fake_call_agent_for_narrative(**kwargs):
        captured.update(kwargs)
        return '{"business_goal":"把 AI 能力装进硬件"}'

    monkeypatch.setattr(
        "ipo_evidence.llm_caller.call_agent_for_narrative",
        fake_call_agent_for_narrative,
    )

    output = call_llm_for_skill(
        skill_name="business_goal_decompose",
        evidence_text="[C-001] 公司主要产品包括 AI 芯片。",
        instruction="只输出 JSON",
    )

    assert output == '{"business_goal":"把 AI 能力装进硬件"}'
    assert "business_goal_decompose" in captured["system_prompt"]
    assert "只输出 JSON" in captured["user_prompt"]
    assert "[C-001] 公司主要产品包括 AI 芯片。" in captured["user_prompt"]
