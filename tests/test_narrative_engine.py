from ipo_evidence.models import EvidencePacket, SkillInterpretation
from ipo_evidence.narrative_engine import _build_user_prompt, generate_narrative


def test_generate_narrative_uses_interpretation_materials_and_trace(monkeypatch):
    def raise_error(**_kwargs):
        raise RuntimeError("agent unavailable")

    monkeypatch.setattr("ipo_evidence.narrative_engine.call_agent_for_narrative", raise_error)

    skill_outputs = [
        SkillInterpretation(
            skill_key="business_goal_decompose",
            interpretation={
                "business_goal": "把 AI 能力装进消费硬件",
                "target_scenario": ["车载", "会议"],
            },
            evidence_chain=["E-001"],
            confidence="high",
            gaps=[],
        ),
        SkillInterpretation(
            skill_key="capability_match",
            interpretation={
                "strengths": ["研发投入持续增长"],
                "weaknesses": ["客户集中度较高"],
                "tension": "增长能力与客户集中风险并存",
            },
            evidence_chain=["E-002"],
            confidence="medium",
            gaps=[],
        ),
    ]

    report_md, trace = generate_narrative(
        all_skill_outputs=skill_outputs,
        evidence_packet=EvidencePacket(doc_id="doc_test", items=[]),
        citation_index={"E-001": "C-001", "E-002": "C-002"},
    )

    assert "把 AI 能力装进消费硬件" in report_md
    assert "[C-001]" in report_md
    assert "增长能力与客户集中风险并存" in report_md
    assert trace["skills_used"] == ["business_goal_decompose", "capability_match"]
    assert trace["total_evidence"] == 2
    assert trace["confidence_distribution"] == {"high": 1, "medium": 1, "low": 0}


def test_generate_narrative_writes_multiple_paragraphs_with_distributed_citations(monkeypatch):
    def raise_error(**_kwargs):
        raise RuntimeError("agent unavailable")

    monkeypatch.setattr("ipo_evidence.narrative_engine.call_agent_for_narrative", raise_error)

    skill_outputs = [
        SkillInterpretation(
            skill_key="business_goal_decompose",
            interpretation={
                "business_goal": "公司专注于全栈对话式 AI 和端侧智能技术",
                "target_scenario": ["智慧出行", "智慧办公"],
            },
            evidence_chain=["E-001"],
            confidence="high",
            gaps=[],
        ),
        SkillInterpretation(
            skill_key="capability_match",
            interpretation={
                "strengths": ["研发投入保持较高水平"],
                "weaknesses": ["经营活动现金流仍为负"],
                "tension": "技术投入与现金流压力同时存在",
            },
            evidence_chain=["E-002", "E-003"],
            confidence="high",
            gaps=[],
        ),
        SkillInterpretation(
            skill_key="reader_value_translate",
            interpretation={
                "for_investors": "投资人应继续验证收入质量和现金流改善。",
            },
            evidence_chain=["E-004"],
            confidence="high",
            gaps=[],
        ),
    ]

    report_md, _trace = generate_narrative(
        skill_outputs,
        EvidencePacket(doc_id="doc_test", items=[]),
        {
            "E-001": "C-001",
            "E-002": "C-002",
            "E-003": "C-003",
            "E-004": "C-004",
        },
    )

    paragraphs = [paragraph for paragraph in report_md.split("\n\n") if paragraph.strip()]
    assert len(paragraphs) >= 2
    assert "[C-001]" in paragraphs[0]
    assert "[C-002]" in report_md or "[C-003]" in report_md
    assert "[C-004]" in report_md
    assert "。、" not in report_md
    assert "。。" not in report_md


def test_generate_narrative_uses_llm_writer(monkeypatch):
    monkeypatch.setattr(
        "ipo_evidence.narrative_engine.call_agent_for_narrative",
        lambda **_kwargs: "LLM 生成的自然文章。[C-001]\n\n第二段继续展开。[C-002]",
    )

    report_md, trace = generate_narrative(
        [
            SkillInterpretation(
                skill_key="business_goal_decompose",
                interpretation={"business_goal": "公司专注对话式 AI"},
                evidence_chain=["E-001"],
                confidence="high",
                gaps=[],
            )
        ],
        EvidencePacket(doc_id="doc_test", items=[]),
        {"E-001": "C-001"},
    )

    assert report_md.startswith("LLM 生成的自然文章")
    assert trace["llm_used"] is True
    assert trace["fallback_used"] is False


def test_generate_narrative_retries_when_trend_section_is_too_short(monkeypatch):
    calls = []
    short_report = "\n\n".join(
        [
            "## 业务标题",
            "业务段落。[C-001]",
            "## 能力标题",
            "能力段落。[C-002]",
            "## 张力标题",
            "张力段落。[C-003]",
            "## 读者标题",
            "### 如果你是该行业的从业者",
            "从业者段落。",
            "### 如果你是消费者",
            "消费者段落。",
            "### 这份招股书揭示的趋势",
            "趋势太短。",
        ]
    )
    long_trend = "趋势分析展开。" * 110
    fixed_report = short_report.replace("趋势太短。", long_trend)

    def fake_call_agent_for_narrative(**kwargs):
        calls.append(kwargs)
        return short_report if len(calls) == 1 else fixed_report

    monkeypatch.setattr(
        "ipo_evidence.narrative_engine.call_agent_for_narrative",
        fake_call_agent_for_narrative,
    )

    report_md, trace = generate_narrative(
        [
            SkillInterpretation(
                skill_key="business_goal_decompose",
                interpretation={"business_goal": "把 AI 能力装进终端硬件"},
                evidence_chain=["E-001"],
                confidence="high",
                gaps=[],
            ),
            SkillInterpretation(
                skill_key="capability_match",
                interpretation={"strengths": ["强项"], "weaknesses": ["弱项"]},
                evidence_chain=["E-002"],
                confidence="high",
                gaps=[],
            ),
            SkillInterpretation(
                skill_key="tension_expand",
                interpretation={"tension_point": "增长与投入并存"},
                evidence_chain=["E-003"],
                confidence="high",
                gaps=[],
            ),
            SkillInterpretation(
                skill_key="reader_value_translate",
                interpretation={
                    "for_practitioners": "从业者建议",
                    "for_consumers": "消费者建议",
                    "trend_tech_position": "技术趋势",
                    "trend_industry_impact": "产业影响",
                    "trend_personal_impact": "个人影响",
                    "trend_big_picture": "更大图景",
                },
                evidence_chain=["E-004"],
                confidence="high",
                gaps=[],
            ),
        ],
        EvidencePacket(doc_id="doc_test", items=[]),
        {"E-001": "C-001", "E-002": "C-002", "E-003": "C-003", "E-004": "C-004"},
    )

    assert len(calls) == 2
    assert "低于 1,400" in calls[1]["user_prompt"]
    assert report_md == fixed_report
    assert trace["llm_used"] is True


def test_generate_narrative_falls_back_when_llm_fails(monkeypatch):
    def raise_error(**_kwargs):
        raise RuntimeError("agent unavailable")

    monkeypatch.setattr("ipo_evidence.narrative_engine.call_agent_for_narrative", raise_error)

    report_md, trace = generate_narrative(
        [
            SkillInterpretation(
                skill_key="business_goal_decompose",
                interpretation={
                    "business_goal": "公司专注于全栈对话式 AI",
                    "target_scenario": ["智慧出行"],
                },
                evidence_chain=["E-001"],
                confidence="high",
                gaps=[],
            )
        ],
        EvidencePacket(doc_id="doc_test", items=[]),
        {"E-001": "C-001"},
    )

    assert "公司专注于全栈对话式 AI" in report_md
    assert trace["llm_used"] is False
    assert trace["fallback_used"] is True


def test_generate_narrative_returns_low_confidence_notice_without_materials():
    report_md, trace = generate_narrative(
        [
            SkillInterpretation(
                skill_key="disclosure_gap_scan",
                interpretation={},
                evidence_chain=[],
                confidence="low",
                gaps=[{"gap": "披露缺口证据不足", "impact": "无法分析"}],
            )
        ],
        EvidencePacket(doc_id="doc_test", items=[]),
        {},
    )

    assert report_md == "当前证据不足以生成高置信度叙事。"
    assert trace["confidence_distribution"] == {"high": 0, "medium": 0, "low": 1}


def test_build_user_prompt_requests_structured_research_report():
    prompt = _build_user_prompt(
        {
            "business_goal_decompose": {
                "business_goal": "把 AI 能力装进终端硬件",
                "product_entry": ["AI 芯片", "智慧办公硬件"],
                "target_scenario": ["智慧出行", "会议"],
                "customer_type": "B2B",
            },
            "capability_match": {
                "strengths": ["产品覆盖多场景"],
                "weaknesses": ["现金流波动"],
                "tension": "多场景放量能力与盈利质量压力并存",
            },
            "tension_expand": {
                "tension_point": "收入增长与现金流压力并存",
                "positive_side": "产品和收入持续扩张",
                "negative_side": "现金流波动和亏损仍需验证",
                "tradeoff_logic": "扩张期投入支撑增长，但短期压低盈利质量",
            },
            "reader_value_translate": {
                "for_practitioners": "从业者应关注标准化产品机会。",
                "for_consumers": "消费者应关注真实体验。",
                "trend_tech_position": "端侧智能进入规模化落地阶段。",
                "trend_industry_impact": "芯片和硬件厂商分工变化。",
                "trend_personal_impact": "相关岗位价值上升。",
                "trend_big_picture": "AI 能力走向商品化。",
            },
        },
        {
            "business_goal_decompose": ["C-001"],
            "capability_match": ["C-002"],
            "tension_expand": ["C-003"],
            "reader_value_translate": ["C-004"],
        },
    )

    assert "总字数不设硬性" in prompt
    assert "4 个二级标题" in prompt
    assert "3 个三级标题" in prompt
    assert "### 如果你是该行业的从业者" in prompt
    assert "### 如果你是消费者" in prompt
    assert "### 这份招股书揭示的趋势" in prompt
    assert "1,400-1,800 字" in prompt
    assert "不要输出一级标题" in prompt
