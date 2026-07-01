from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from ipo_evidence.config import load_yaml
from ipo_evidence.paths import repo_root


@dataclass(frozen=True)
class PromptConfig:
    prompt_slot: str
    purpose: str
    rules: list[str]


@dataclass(frozen=True)
class SkillConfig:
    skill_key: str
    title: str
    action: str
    requires: list[str]
    produces: list[str]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _yaml_files(relative_dir: str) -> list[Path]:
    config_dir = repo_root() / relative_dir
    return sorted(config_dir.glob("*.yaml"))


@cache
def _prompt_index() -> dict[str, PromptConfig]:
    prompts: dict[str, PromptConfig] = {}
    for path in _yaml_files("configs/prompts"):
        data = load_yaml(path.relative_to(repo_root()).as_posix())
        prompt = PromptConfig(
            prompt_slot=data["prompt_slot"],
            purpose=data["purpose"],
            rules=_string_list(data.get("rules")),
        )
        prompts[prompt.prompt_slot] = prompt
    return prompts


@cache
def _skill_index() -> dict[str, SkillConfig]:
    skills: dict[str, SkillConfig] = {}
    for path in _yaml_files("configs/skills"):
        data = load_yaml(path.relative_to(repo_root()).as_posix())
        skill = SkillConfig(
            skill_key=data["skill_key"],
            title=data["title"],
            action=data["action"],
            requires=_string_list(data.get("requires")),
            produces=_string_list(data.get("produces")),
        )
        skills[skill.skill_key] = skill
    return skills


def load_prompt_config(prompt_slot: str) -> PromptConfig:
    prompts = _prompt_index()
    if prompt_slot not in prompts:
        raise ValueError(f"unknown prompt_slot: {prompt_slot}")
    prompt = prompts[prompt_slot]
    return PromptConfig(
        prompt_slot=prompt.prompt_slot,
        purpose=prompt.purpose,
        rules=list(prompt.rules),
    )


def load_skill_configs(skill_refs: list[str]) -> list[SkillConfig]:
    skills = _skill_index()
    loaded: list[SkillConfig] = []
    for skill_ref in skill_refs:
        if skill_ref not in skills:
            raise ValueError(f"unknown skill_ref: {skill_ref}")
        skill = skills[skill_ref]
        loaded.append(
            SkillConfig(
                skill_key=skill.skill_key,
                title=skill.title,
                action=skill.action,
                requires=list(skill.requires),
                produces=list(skill.produces),
            )
        )
    return loaded
