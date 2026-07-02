import pytest

from ipo_evidence.report_runtime import (
    _string_list,
    load_prompt_config,
    load_skill_package_config,
    load_skill_configs,
)


def test_load_prompt_config_by_prompt_slot():
    prompt = load_prompt_config("narrative_section")

    assert prompt.prompt_slot == "narrative_section"
    assert prompt.purpose == "把一个 section draft 写成自然正文。"
    assert "事实句必须带 citation id。" in prompt.rules


def test_load_prompt_config_returns_defensive_copy():
    prompt = load_prompt_config("narrative_section")
    prompt.rules.append("mutated")

    fresh_prompt = load_prompt_config("narrative_section")

    assert "mutated" not in fresh_prompt.rules


def test_load_skill_configs_keeps_request_order():
    skills = load_skill_configs(["capability_match", "business_goal_decompose"])

    assert [skill.skill_key for skill in skills] == [
        "capability_match",
        "business_goal_decompose",
    ]
    assert skills[0].title == "能力匹配"
    assert skills[1].produces == ["business_question", "structured_conclusion"]


def test_load_skill_configs_includes_structured_output_schema():
    skill = load_skill_configs(["business_goal_decompose"])[0]

    assert skill.output_schema["interpretation"]["business_goal"] == "string"
    assert skill.output_schema["evidence_chain"] == "list[string]"


def test_load_skill_configs_returns_defensive_copy():
    skills = load_skill_configs(["capability_match"])
    skills[0].requires.append("mutated")
    skills[0].produces.append("mutated")
    skills[0].output_schema["interpretation"] = {}

    fresh_skills = load_skill_configs(["capability_match"])

    assert "mutated" not in fresh_skills[0].requires
    assert "mutated" not in fresh_skills[0].produces
    assert fresh_skills[0].output_schema["interpretation"]


def test_load_skill_package_config():
    package = load_skill_package_config("ipo_prospectus_analysis")

    assert package.package_key == "ipo_prospectus_analysis"
    assert package.skills == [
        "business_goal_decompose",
        "capability_match",
        "disclosure_gap_scan",
        "tension_expand",
        "reader_value_translate",
    ]
    package.skills.append("mutated")

    fresh_package = load_skill_package_config("ipo_prospectus_analysis")

    assert "mutated" not in fresh_package.skills


def test_load_skill_configs_rejects_unknown_skill():
    with pytest.raises(ValueError, match="unknown skill_ref: missing_skill"):
        load_skill_configs(["missing_skill"])


def test_load_prompt_config_rejects_unknown_prompt_slot():
    with pytest.raises(ValueError, match="unknown prompt_slot: missing_prompt"):
        load_prompt_config("missing_prompt")


def test_narrative_writer_prompt_targets_structured_research_report():
    prompt = load_prompt_config("narrative_writer")

    assert "结构化" in prompt.purpose
    assert any("总字数不设硬性" in rule for rule in prompt.rules)
    assert any("4 个二级标题" in rule for rule in prompt.rules)
    assert any("3 个三级标题" in rule for rule in prompt.rules)
    assert any("趋势分析" in rule for rule in prompt.rules)


def test_string_list_ignores_invalid_yaml_values():
    assert _string_list(None) == []
    assert _string_list("not a list") == []
    assert _string_list(["keep", "", 1, None, "also keep"]) == ["keep", "also keep"]
