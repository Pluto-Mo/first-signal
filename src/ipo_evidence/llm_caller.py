from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

from ipo_evidence.paths import repo_root


_SENSITIVE_ENV_NAME = re.compile(r"TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL", re.IGNORECASE)


def call_agent_for_narrative(
    user_prompt: str,
    system_prompt: str,
    timeout: int = 120,
    *,
    agent_command: str = "codex",
    cwd: Path | None = None,
) -> str:
    workspace = cwd or _default_agent_workspace()
    workspace.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        output_path = Path(handle.name)

    prompt = f"{system_prompt.strip()}\n\n---\n\n{user_prompt.strip()}\n"
    cmd = [
        *_resolve_agent_command(agent_command),
        "exec",
        "--cd",
        str(workspace),
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(output_path),
        "-",
    ]

    try:
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                env=_filtered_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(f"Agent CLI timed out after {timeout}s") from error
        except OSError as error:
            raise RuntimeError(f"Agent CLI not available: {redact_env_secrets(str(error))}") from error

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            raise RuntimeError(
                f"Agent CLI failed (exit {result.returncode}): {redact_env_secrets(error_msg)}"
            )

        output = _read_last_message(output_path) or result.stdout.strip()
        if not output:
            raise RuntimeError("Agent CLI returned empty output")
        return redact_env_secrets(output.strip())
    finally:
        output_path.unlink(missing_ok=True)


def call_llm_for_skill(
    skill_name: str,
    evidence_text: str,
    instruction: str,
) -> str:
    system_prompt = f"""你是招股书分析专家，正在执行 {skill_name} 分析任务。

请严格按照指令要求，用 JSON 格式输出分析结果。
不要输出任何解释、注释或元信息，只输出 JSON。
确保 JSON 格式正确，可以被 json.loads() 解析。"""
    user_prompt = f"""{instruction}

证据：
{evidence_text}
"""
    return call_agent_for_narrative(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
    )


def redact_env_secrets(text: str) -> str:
    redacted = text
    for value in _sensitive_env_values(os.environ):
        redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def _default_agent_workspace() -> Path:
    return repo_root() / "data" / "tmp" / "agent_workspace"


def _filtered_env() -> dict[str, str]:
    return {name: value for name, value in os.environ.items() if not _is_sensitive_env_name(name)}


def _sensitive_env_values(env: Mapping[str, str]) -> list[str]:
    return [
        value
        for name, value in env.items()
        if _is_sensitive_env_name(name) and len(value) >= 8
    ]


def _is_sensitive_env_name(name: str) -> bool:
    return bool(_SENSITIVE_ENV_NAME.search(name))


def _resolve_agent_command(agent_command: str) -> list[str]:
    if os.name != "nt":
        return [agent_command]

    cmd_path = shutil.which(f"{agent_command}.cmd")
    if cmd_path:
        return [cmd_path]

    resolved = shutil.which(agent_command)
    if not resolved:
        return [agent_command]

    if resolved.lower().endswith(".ps1"):
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", resolved]
    return [resolved]


def _read_last_message(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
