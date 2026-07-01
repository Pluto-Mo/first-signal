from ipo_evidence.models import EvidenceItem, QualityStatus
from ipo_evidence.report_runtime import PromptConfig, SkillConfig
from ipo_evidence.section_writer import write_section


def _text_item(evidence_id: str, summary: str, section: str = "business_and_product") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        canonical_section=section,
        claim_summary=summary,
        source_type="text_quote",
        source_file="sample.pdf",
        page_number=2,
        block_id=f"B-{evidence_id}",
        section_path=["业务和技术"],
        quote=summary,
        quality_status=QualityStatus.safe_to_use,
    )


def _table_item(evidence_id: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        canonical_section="financials",
        claim_summary="发行人主要财务数据及财务指标中，营业收入（万元）对应数据为：{'项目': '营业收入（万元）', '2025年度': '68,771.52', '2024年度': '60,077.16'}。",
        source_type="table_fact",
        source_file="sample.pdf",
        page_number=11,
        table_id="T-001",
        table_title="主要财务数据及财务指标",
        section_path=["财务会计信息"],
        fields={
            "项目": "营业收入（万元）",
            "2025年度": "68,771.52",
            "2024年度": "60,077.16",
        },
        quality_status=QualityStatus.safe_to_use,
    )


def test_write_section_limits_evidence_and_adds_interpretation():
    items = [
        (index, _text_item(f"E-{index:03d}", f"公司在智慧出行、智慧办公和智慧物联场景形成产品化交付能力，样本 {index}。"))
        for index in range(1, 31)
    ]

    result = write_section(
        section_key="company_and_industry",
        title="公司介绍与行业概况",
        skill_refs=["business_goal_decompose", "capability_match", "reader_value_translate"],
        prompt_slot="narrative_section",
        indexed_items=items,
    )

    assert len(result.selected_items) <= 12
    assert 2 <= len([part for part in result.body.split("\n\n") if part.strip()]) <= 6
    assert result.body.count("[C-") <= 12
    assert "阅读这一节" in result.body
    assert "不是把 AI 当成概念标签" in result.body
    assert "{'" not in result.body
    assert "对应数据为" not in result.body


def test_write_section_formats_table_fields_without_raw_dict_literals():
    result = write_section(
        section_key="personal_investment",
        title="个人投资视角",
        skill_refs=["business_goal_decompose", "tension_expand"],
        prompt_slot="narrative_section",
        indexed_items=[(7, _table_item("E-007"))],
    )

    assert "营业收入（万元）" in result.body
    assert "2025年度为 68,771.52" in result.body
    assert "2024年度为 60,077.16" in result.body
    assert "[C-007]" in result.body
    assert "{'" not in result.body
    assert "对应数据为" not in result.body


def test_write_section_normalizes_table_field_key_line_breaks():
    item = _table_item("E-008")
    item.fields = {
        "项目": "营业收入（万元）",
        "2025-12-31/\\n2025 年度": "68,771.52",
        "2024-12-31/\n2024 年度": "60,077.16",
    }

    result = write_section(
        section_key="personal_investment",
        title="个人投资视角",
        skill_refs=["business_goal_decompose", "tension_expand"],
        prompt_slot="narrative_section",
        indexed_items=[(8, item)],
    )

    assert "2025-12-31/ 2025 年度为 68,771.52" in result.body
    assert "2024-12-31/ 2024 年度为 60,077.16" in result.body
    assert "\\n" not in result.body


def test_write_section_keeps_plain_text_value_after_corresponding_data_phrase():
    result = write_section(
        section_key="personal_investment",
        title="个人投资视角",
        skill_refs=["business_goal_decompose"],
        prompt_slot="narrative_section",
        indexed_items=[
            (
                1,
                _text_item(
                    "E-001",
                    "报告期内，公司营业收入对应数据为 68,771.52 万元，保持增长。",
                    "financials",
                ),
            )
        ],
    )

    assert "68,771.52" in result.body
    assert "[C-001]" in result.body
    assert "{'" not in result.body
    assert "对应数据为" not in result.body


def test_write_section_keeps_renderable_table_fact_with_low_value_summary_template():
    item = EvidenceItem(
        evidence_id="E-012",
        canonical_section="financials",
        claim_summary="合并利润表中，营业收入对应数据为：{'项目': '营业收入', '2025年度': '68,771.52'}",
        source_type="table_fact",
        source_file="sample.pdf",
        page_number=12,
        table_id="T-012",
        table_title="合并利润表",
        section_path=["财务会计信息", "合并利润表"],
        fields={
            "项目": "营业收入",
            "2025年度": "68,771.52",
        },
        quality_status=QualityStatus.safe_to_use,
    )

    result = write_section(
        section_key="personal_investment",
        title="个人投资视角",
        skill_refs=["business_goal_decompose"],
        prompt_slot="narrative_section",
        indexed_items=[(12, item)],
    )

    assert "营业收入" in result.body
    assert "2025年度为 68,771.52" in result.body
    assert "[C-012]" in result.body
    assert [selected.evidence_id for _, selected in result.selected_items] == ["E-012"]
    assert "{'" not in result.body
    assert "对应数据为" not in result.body


def test_write_section_skips_broken_and_low_value_evidence_when_readable_option_exists():
    items = [
        (
            1,
            _text_item(
                "E-001",
                "报告期内，公司专注于全栈对话式 AI 和端侧智能技术的自主研发，主营业务未发生重大变化。公司结合自身战略、技术水平、产品特点、行业整体情况以及自身所处。",
            ),
        ),
        (
            2,
            _text_item(
                "E-002",
                "随着全球人工智能产业的快速发展，芯片、云计算及 IDC 服务作为人工智能产业的上游基础设施，在。",
            ),
        ),
        (
            3,
            _text_item(
                "E-003",
                "公司聚焦智慧出行、智慧办公和智慧物联三大领域，主营业务收入规模持续增长，毛利率整体保持较高水平。",
            ),
        ),
    ]

    result = write_section(
        section_key="company_and_industry",
        title="公司介绍与行业概况",
        skill_refs=["business_goal_decompose"],
        prompt_slot="narrative_section",
        indexed_items=items,
    )

    assert "公司聚焦智慧出行、智慧办公和智慧物联三大领域" in result.body
    assert "自身所处" not in result.body
    assert "上游基础设施，在" not in result.body
    assert "主营业务未发生重大变化" not in result.body
    assert [item.evidence_id for _, item in result.selected_items] == ["E-003"]


def test_write_section_executes_tension_skill_when_requested():
    items = [
        (1, _text_item("E-001", "报告期内，公司营业收入持续增长。", "financials")),
        (2, _text_item("E-002", "报告期内，公司经营活动现金流量净额持续为负。", "financials")),
    ]

    result = write_section(
        section_key="cognitive_worldview",
        title="认知世界的方式",
        skill_refs=["tension_expand"],
        prompt_slot="narrative_section",
        indexed_items=items,
    )

    assert "张力" in result.body
    assert "增长" in result.body
    assert "现金流" in result.body


def test_write_section_loads_skill_config_action_text():
    result = write_section(
        section_key="company_and_industry",
        title="公司介绍与行业概况",
        skill_refs=["capability_match"],
        prompt_slot="narrative_section",
        indexed_items=[
            (
                1,
                _text_item(
                    "E-001",
                    "公司产品覆盖智慧出行和智慧办公场景，并形成客户交付记录。",
                ),
            )
        ],
    )

    assert "检查产品、研发、客户和交付能力" in result.body
    assert "[C-001]" in result.body


def test_write_section_uses_prompt_rules_to_clean_internal_terms(monkeypatch):
    def fake_load_skill_configs(skill_refs: list[str]) -> list[SkillConfig]:
        return [
            SkillConfig(
                skill_key="capability_match",
                title="能力匹配",
                action="本节调用的解读动作是：prompt_slot skill_refs section draft internal trace 检查产品、研发、客户和交付能力。",
                requires=[],
                produces=[],
            )
        ]

    def fake_prompt_without_rule(prompt_slot: str) -> PromptConfig:
        return PromptConfig(prompt_slot=prompt_slot, purpose="", rules=[])

    def fake_prompt_with_rule(prompt_slot: str) -> PromptConfig:
        return PromptConfig(
            prompt_slot=prompt_slot,
            purpose="",
            rules=["不写内部系统词。", "事实句必须带 citation id。"],
        )

    monkeypatch.setattr(
        "ipo_evidence.section_writer.load_skill_configs",
        fake_load_skill_configs,
    )
    monkeypatch.setattr(
        "ipo_evidence.section_writer.load_prompt_config",
        fake_prompt_without_rule,
    )

    result_without_rule = write_section(
        section_key="company_and_industry",
        title="公司介绍与行业概况",
        skill_refs=["capability_match"],
        prompt_slot="narrative_section",
        indexed_items=[
            (
                1,
                _text_item(
                    "E-001",
                    "公司产品覆盖智慧出行和智慧办公场景，并形成客户交付记录。",
                ),
            )
        ],
    )

    assert "prompt_slot" in result_without_rule.body

    monkeypatch.setattr(
        "ipo_evidence.section_writer.load_prompt_config",
        fake_prompt_with_rule,
    )

    result_with_rule = write_section(
        section_key="company_and_industry",
        title="公司介绍与行业概况",
        skill_refs=["capability_match"],
        prompt_slot="narrative_section",
        indexed_items=[
            (
                1,
                _text_item(
                    "E-001",
                    "公司产品覆盖智慧出行和智慧办公场景，并形成客户交付记录。",
                ),
            )
        ],
    )

    assert "检查产品、研发、客户和交付能力" in result_with_rule.body
    assert "[C-001]" in result_with_rule.body
    assert "本节调用的解读动作是" not in result_with_rule.body
    assert "prompt_slot" not in result_with_rule.body
    assert "skill_refs" not in result_with_rule.body
    assert "section draft" not in result_with_rule.body
    assert "internal trace" not in result_with_rule.body


def test_write_section_rejects_unknown_prompt_slot():
    try:
        write_section(
            section_key="company_and_industry",
            title="公司介绍与行业概况",
            skill_refs=[],
            prompt_slot="missing_prompt",
            indexed_items=[],
        )
    except ValueError as exc:
        assert "unknown prompt_slot: missing_prompt" in str(exc)
    else:
        raise AssertionError("write_section should reject unknown prompt_slot")


def test_write_section_rejects_unknown_skill_ref():
    try:
        write_section(
            section_key="company_and_industry",
            title="公司介绍与行业概况",
            skill_refs=["missing_skill"],
            prompt_slot="narrative_section",
            indexed_items=[],
        )
    except ValueError as exc:
        assert "unknown skill_ref: missing_skill" in str(exc)
    else:
        raise AssertionError("write_section should reject unknown skill_ref")
