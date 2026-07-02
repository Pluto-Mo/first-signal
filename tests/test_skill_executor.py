import pytest

from ipo_evidence.models import EvidenceItem, EvidencePacket, QualityStatus
from ipo_evidence.skill_executor import execute_skill


def _packet() -> EvidencePacket:
    return EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="business_and_product",
                claim_summary="公司主要产品包括 AI 芯片和智慧办公硬件，覆盖智慧出行和会议场景。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                block_id="B-001",
                section_path=["业务和技术"],
                quote="公司主要产品包括 AI 芯片和智慧办公硬件，覆盖智慧出行和会议场景。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="financials",
                claim_summary="报告期内公司研发费用持续增长，营业收入也持续增长。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=4,
                block_id="B-002",
                section_path=["财务会计信息"],
                quote="报告期内公司研发费用持续增长，营业收入也持续增长。",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-003",
                canonical_section="risks",
                claim_summary="公司存在客户集中度较高和现金流波动风险。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=5,
                block_id="B-003",
                section_path=["风险因素"],
                quote="公司存在客户集中度较高和现金流波动风险。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )


@pytest.fixture(autouse=True)
def stub_skill_llm(monkeypatch):
    def fake_call_claude_for_skill(**kwargs):
        skill_name = kwargs["skill_name"]
        if skill_name == "business_goal_decompose":
            return """
            {
              "business_goal": "把 AI 能力装进终端硬件",
              "product_entry": ["AI 芯片", "智慧办公硬件"],
              "target_scenario": ["智慧出行", "会议"],
              "customer_type": "B2B",
              "revenue_structure": "硬件和解决方案收入为主"
            }
            """
        if skill_name == "capability_match":
            return """
            {
              "strengths": ["产品覆盖多场景", "研发投入持续"],
              "weaknesses": ["现金流波动", "客户集中风险"],
              "tension": "多场景放量能力与盈利质量压力并存",
              "resource_allocation": "资源集中投向研发和场景交付"
            }
            """
        if skill_name == "tension_expand":
            return """
            {
              "tension_point": "收入增长与现金流压力并存",
              "positive_side": "产品和收入持续扩张",
              "negative_side": "现金流波动和亏损仍需验证",
              "tradeoff_logic": "扩张期投入支撑增长，但短期压低盈利质量",
              "future_path": ["提高客户分散度", "验证研发转化效率"]
            }
            """
        if skill_name == "reader_value_translate":
            return """
            {
              "for_practitioners": "从业者应关注标准化产品机会和长尾场景切入。",
              "for_consumers": "消费者应优先选择已被车载和办公场景验证的产品。",
              "trend_tech_position": "端侧智能处在从概念验证走向规模化落地的阶段。",
              "trend_industry_impact": "芯片、模组、硬件厂商和方案商的分工会被重新分配。",
              "trend_personal_impact": "端侧模型适配、场景产品和硬件工程岗位价值上升。",
              "trend_big_picture": "AI 能力会像摄像头模组一样被商品化，进入更多终端。"
            }
            """
        return "{}"

    monkeypatch.setattr("ipo_evidence.skill_executor.call_claude_for_skill", fake_call_claude_for_skill)


def test_execute_business_goal_decompose_returns_interpretation_payload():
    output = execute_skill(
        skill_key="business_goal_decompose",
        evidence_refs=[
            {"evidence_id": "E-001", "rank": 1},
            {"evidence_id": "E-999", "rank": 2},
        ],
        evidence_packet=_packet(),
        citation_index={"E-001": "C-001"},
    )

    assert output.skill_key == "business_goal_decompose"
    assert output.confidence == "high"
    assert output.evidence_chain == ["E-001"]
    assert "business_goal" in output.interpretation
    assert "product_entry" in output.interpretation
    assert output.gaps == []


def test_execute_business_goal_decompose_uses_llm_analysis(monkeypatch):
    calls = []

    def fake_call_claude_for_skill(**kwargs):
        calls.append(kwargs)
        return """
        {
          "business_goal": "把 AI 能力装进终端硬件",
          "product_entry": ["AI 芯片", "智慧办公硬件"],
          "target_scenario": ["智慧出行", "会议"],
          "customer_type": "B2B",
          "revenue_structure": "硬件和解决方案收入为主"
        }
        """

    monkeypatch.setattr(
        "ipo_evidence.skill_executor.call_claude_for_skill",
        fake_call_claude_for_skill,
        raising=False,
    )

    output = execute_skill(
        "business_goal_decompose",
        [{"evidence_id": "E-001", "rank": 1}, {"evidence_id": "E-002", "rank": 2}],
        _packet(),
        {"E-001": "C-001", "E-002": "C-002"},
    )

    assert calls
    assert calls[0]["skill_name"] == "business_goal_decompose"
    assert "[C-001]" in calls[0]["evidence_text"]
    assert output.interpretation["business_goal"] == "把 AI 能力装进终端硬件"
    assert len(output.interpretation["business_goal"]) < 100
    assert output.confidence == "high"


def test_execute_capability_match_returns_strengths_weaknesses_and_tension():
    output = execute_skill(
        skill_key="capability_match",
        evidence_refs=[
            {"evidence_id": "E-001", "rank": 1},
            {"evidence_id": "E-002", "rank": 2},
            {"evidence_id": "E-003", "rank": 3},
        ],
        evidence_packet=_packet(),
        citation_index={"E-001": "C-001", "E-002": "C-002", "E-003": "C-003"},
    )

    assert output.skill_key == "capability_match"
    assert output.interpretation["strengths"]
    assert output.interpretation["weaknesses"]
    assert "tension" in output.interpretation
    assert output.evidence_chain == ["E-001", "E-002", "E-003"]


def test_execute_capability_match_uses_llm_and_limits_core_points(monkeypatch):
    def fake_call_claude_for_skill(**_kwargs):
        return """
        {
          "strengths": ["产品覆盖多场景", "研发投入持续", "客户验证明确"],
          "weaknesses": ["现金流波动", "客户集中风险"],
          "tension": "多场景放量能力与盈利质量压力并存",
          "resource_allocation": "资源集中投向研发和场景交付"
        }
        """

    monkeypatch.setattr(
        "ipo_evidence.skill_executor.call_claude_for_skill",
        fake_call_claude_for_skill,
        raising=False,
    )

    output = execute_skill(
        "capability_match",
        [
            {"evidence_id": "E-001", "rank": 1},
            {"evidence_id": "E-002", "rank": 2},
            {"evidence_id": "E-003", "rank": 3},
        ],
        _packet(),
        {"E-001": "C-001", "E-002": "C-002", "E-003": "C-003"},
    )

    assert output.interpretation["tension"] == "多场景放量能力与盈利质量压力并存"
    assert len(output.interpretation["strengths"]) <= 5
    assert len(output.interpretation["weaknesses"]) <= 5
    assert output.confidence == "high"


def test_execute_tension_expand_uses_llm_tradeoff_logic(monkeypatch):
    def fake_call_claude_for_skill(**_kwargs):
        return """
        {
          "tension_point": "收入增长与现金流压力并存",
          "positive_side": "产品和收入持续扩张",
          "negative_side": "现金流波动和亏损仍需验证",
          "tradeoff_logic": "扩张期投入支撑增长，但短期压低盈利质量",
          "future_path": ["提高客户分散度", "验证研发转化效率"]
        }
        """

    monkeypatch.setattr(
        "ipo_evidence.skill_executor.call_claude_for_skill",
        fake_call_claude_for_skill,
        raising=False,
    )

    output = execute_skill(
        "tension_expand",
        [
            {"evidence_id": "E-001", "rank": 1},
            {"evidence_id": "E-002", "rank": 2},
            {"evidence_id": "E-003", "rank": 3},
        ],
        _packet(),
        {"E-001": "C-001", "E-002": "C-002", "E-003": "C-003"},
    )

    assert output.interpretation["tension_point"] == "收入增长与现金流压力并存"
    assert "扩张期投入支撑增长" in output.interpretation["tradeoff_logic"]
    assert len(output.interpretation["future_path"]) == 2


def test_execute_reader_value_translate_uses_llm_deep_trend_fields(monkeypatch):
    calls = []

    def fake_call_claude_for_skill(**kwargs):
        calls.append(kwargs)
        return """
        {
          "for_practitioners": "从业者应关注标准化产品机会和长尾场景切入。",
          "for_consumers": "消费者应优先选择已被车载和办公场景验证的产品。",
          "trend_tech_position": "端侧智能处在从概念验证走向规模化落地的阶段。",
          "trend_industry_impact": "芯片、模组、硬件厂商和方案商的分工会被重新分配。",
          "trend_personal_impact": "端侧模型适配、场景产品和硬件工程岗位价值上升。",
          "trend_big_picture": "AI 能力会像摄像头模组一样被商品化，进入更多终端。"
        }
        """

    monkeypatch.setattr("ipo_evidence.skill_executor.call_claude_for_skill", fake_call_claude_for_skill)

    output = execute_skill(
        "reader_value_translate",
        [
            {"evidence_id": "E-001", "rank": 1},
            {"evidence_id": "E-002", "rank": 2},
            {"evidence_id": "E-003", "rank": 3},
        ],
        _packet(),
        {"E-001": "C-001", "E-002": "C-002", "E-003": "C-003"},
    )

    assert calls
    assert calls[0]["skill_name"] == "reader_value_translate"
    assert calls[0]["max_tokens"] >= 3000
    assert "趋势" in calls[0]["instruction"]
    assert output.interpretation["trend_tech_position"]
    assert output.interpretation["trend_industry_impact"]
    assert output.interpretation["trend_personal_impact"]
    assert output.interpretation["trend_big_picture"]


def test_execute_reader_value_translate_falls_back_when_agent_fails(monkeypatch):
    monkeypatch.setattr(
        "ipo_evidence.skill_executor.call_claude_for_skill",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("agent unavailable")),
    )

    output = execute_skill(
        "reader_value_translate",
        [
            {"evidence_id": "E-001", "rank": 1},
            {"evidence_id": "E-002", "rank": 2},
            {"evidence_id": "E-003", "rank": 3},
        ],
        _packet(),
        {"E-001": "C-001", "E-002": "C-002", "E-003": "C-003"},
    )

    assert output.interpretation["for_practitioners"]
    assert output.interpretation["trend_big_picture"]
    assert output.confidence in {"high", "medium"}


def test_execute_llm_skill_falls_back_when_agent_fails(monkeypatch):
    def raise_error(**_kwargs):
        raise RuntimeError("agent unavailable")

    monkeypatch.setattr(
        "ipo_evidence.skill_executor.call_claude_for_skill",
        raise_error,
        raising=False,
    )

    output = execute_skill(
        "capability_match",
        [
            {"evidence_id": "E-001", "rank": 1},
            {"evidence_id": "E-002", "rank": 2},
            {"evidence_id": "E-003", "rank": 3},
        ],
        _packet(),
        {"E-001": "C-001", "E-002": "C-002", "E-003": "C-003"},
    )

    assert output.interpretation["strengths"]
    assert output.interpretation["weaknesses"]
    assert output.confidence in {"high", "medium"}


def test_execute_skill_interpretation_uses_readable_compact_text(monkeypatch):
    monkeypatch.setattr(
        "ipo_evidence.skill_executor.call_claude_for_skill",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("agent unavailable")),
    )

    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="financials",
                claim_summary="所属行业的代表性业务指标情况中，主营业务毛利率对应数据为：{'业务指标': '主营业务毛利率', '2025 年度': '63.24%'}。",
                source_type="table_fact",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                table_id="T-001",
                table_title="所属行业的代表性业务指标情况",
                section_path=["财务会计信息"],
                fields={"业务指标": "主营业务毛利率", "2025 年度": "63.24%"},
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="risks",
                claim_summary="公司存在未来一段时期内持续亏损的风险，经营活动现金流量净额持续为负。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=4,
                block_id="B-002",
                section_path=["风险因素"],
                quote="公司存在未来一段时期内持续亏损的风险，经营活动现金流量净额持续为负。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )

    output = execute_skill(
        "capability_match",
        [{"evidence_id": "E-001", "rank": 1}, {"evidence_id": "E-002", "rank": 2}],
        packet,
        {"E-001": "C-001", "E-002": "C-002"},
    )

    rendered = str(output.interpretation)
    assert "{'业务指标'" not in rendered
    assert "持续亏损" in rendered


def test_execute_skill_filters_low_value_transition_fragments(monkeypatch):
    monkeypatch.setattr(
        "ipo_evidence.skill_executor.call_claude_for_skill",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("agent unavailable")),
    )

    packet = EvidencePacket(
        doc_id="doc_test",
        items=[
            EvidenceItem(
                evidence_id="E-001",
                canonical_section="financials",
                claim_summary="结合行业特点，公司选取主营业务收入、主营业务毛利率和研发费用三个具有代表性的业务指标进行分析，具体分析如下：",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=3,
                block_id="B-001",
                section_path=["财务会计信息"],
                quote="结合行业特点，公司选取主营业务收入、主营业务毛利率和研发费用三个具有代表性的业务指标进行分析，具体分析如下：",
                quality_status=QualityStatus.safe_to_use,
            ),
            EvidenceItem(
                evidence_id="E-002",
                canonical_section="risks",
                claim_summary="公司存在客户集中度较高和经营活动现金流量净额持续为负的风险。",
                source_type="text_quote",
                source_file="测试股份有限公司招股说明书.pdf",
                page_number=4,
                block_id="B-002",
                section_path=["风险因素"],
                quote="公司存在客户集中度较高和经营活动现金流量净额持续为负的风险。",
                quality_status=QualityStatus.safe_to_use,
            ),
        ],
    )

    output = execute_skill(
        "capability_match",
        [{"evidence_id": "E-001", "rank": 1}, {"evidence_id": "E-002", "rank": 2}],
        packet,
        {"E-001": "C-001", "E-002": "C-002"},
    )

    rendered = str(output.interpretation)
    assert "具体分析如下" not in rendered
    assert "客户集中度较高" in rendered


def test_execute_skill_records_gap_when_no_relevant_evidence():
    output = execute_skill(
        skill_key="business_goal_decompose",
        evidence_refs=[{"evidence_id": "E-003", "rank": 1}],
        evidence_packet=_packet(),
        citation_index={"E-003": "C-003"},
    )

    assert output.interpretation == {}
    assert output.confidence == "low"
    assert output.gaps[0]["gap"] == "业务目标相关证据不足"


def test_execute_skill_rejects_unknown_skill():
    with pytest.raises(ValueError, match="unknown skill_ref: missing_skill"):
        execute_skill("missing_skill", [], _packet(), {})
