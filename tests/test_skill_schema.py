import pytest
from pydantic import ValidationError

from ipo_evidence.models import SkillInterpretation


def test_skill_interpretation_schema_accepts_freeform_payload():
    interpretation = SkillInterpretation(
        skill_key="business_goal_decompose",
        interpretation={
            "business_goal": "把 AI 能力装进消费硬件",
            "product_entry": ["智能音箱", "车载设备"],
            "target_scenario": ["车载", "会议"],
        },
        evidence_chain=["E-001", "E-002"],
        confidence="high",
        gaps=[],
    )

    assert interpretation.skill_key == "business_goal_decompose"
    assert interpretation.interpretation["business_goal"] == "把 AI 能力装进消费硬件"
    assert isinstance(interpretation.interpretation["product_entry"], list)


def test_skill_interpretation_rejects_unknown_confidence():
    with pytest.raises(ValidationError):
        SkillInterpretation(
            skill_key="business_goal_decompose",
            interpretation={},
            evidence_chain=["E-001"],
            confidence="certain",
            gaps=[],
        )
