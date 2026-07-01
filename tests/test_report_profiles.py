import pytest

from ipo_evidence.evidence import build_evidence_packet
from ipo_evidence.models import Block
from ipo_evidence.report_profiles import load_report_profile, select_report_profile


def _packet(text: str):
    return build_evidence_packet(
        doc_id="doc_test",
        source_file="sample.pdf",
        blocks=[
            Block(
                block_id="B-001",
                page_number=1,
                text=text,
                section_path=["业务与技术"],
            )
        ],
        tables=[],
    )


def test_load_report_profile_merges_base_attention_fields():
    profile = load_report_profile("consumer_product")

    assert profile.profile_key == "consumer_product"
    assert profile.title == "消费产品公司解读"
    assert "产品定位" in profile.attention_fields


def test_load_report_profile_inherits_and_dedupes_attention_fields():
    profile = load_report_profile("technology_company")

    assert "产品入口" in profile.attention_fields
    assert "核心技术" in profile.attention_fields
    assert profile.attention_fields.count("客户验证") == 1


def test_load_report_profile_uses_declared_profile_key(monkeypatch):
    monkeypatch.setattr(
        "ipo_evidence.report_profiles._load_profile_yaml",
        lambda profile_key: {
            "profile_key": "declared_key",
            "title": "Declared",
            "attention_fields": [],
        }
        if profile_key == "alias"
        else {},
    )

    profile = load_report_profile("alias")

    assert profile.profile_key == "declared_key"


def test_load_report_profile_rejects_unknown_profile():
    with pytest.raises(ValueError, match="unknown report profile: missing_profile"):
        load_report_profile("missing_profile")


def test_select_report_profile_defaults_to_base():
    profile_key = select_report_profile("测试股份有限公司", _packet("公司主营业务为软件销售。"))

    assert profile_key == "base"


def test_select_report_profile_detects_technology_company():
    profile_key = select_report_profile(
        "测试股份有限公司",
        _packet("公司核心技术包括 AI 芯片、算法、研发平台和专利，主要产品已实现销售。"),
    )

    assert profile_key == "technology_company"


def test_select_report_profile_does_not_treat_generic_r_and_d_as_technology():
    profile_key = select_report_profile(
        "测试股份有限公司",
        _packet("公司持续研发并取得专利，同时通过渠道和供应链组织消费产品销售，主要产品已实现销售。"),
    )

    assert profile_key == "consumer_product"


def test_select_report_profile_does_not_treat_ai_tool_usage_as_technology():
    profile_key = select_report_profile(
        "测试股份有限公司",
        _packet("公司使用 AI 工具辅助研发，同时通过渠道和供应链组织消费产品销售，主要产品已实现销售。"),
    )

    assert profile_key == "consumer_product"
