from pathlib import Path

import pytest

from ipo_evidence.parser import create_parser
from ipo_evidence.parser.api_stub import ApiStubParser
from ipo_evidence.parser.paddleocr_vl import PaddleOCRVLParser


def test_create_parser_returns_api_stub_for_stub_provider():
    parser = create_parser(
        {"provider": "api_stub"},
        fixture_path=Path("tests/fixtures/sample_prospectus.txt"),
    )

    assert isinstance(parser, ApiStubParser)


def test_create_parser_requires_token_for_paddle_provider(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("PADDLEOCR_API_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="PADDLEOCR_API_TOKEN"):
        create_parser(
            {
                "provider": "paddleocr_vl",
                "token_env_var": "PADDLEOCR_API_TOKEN",
            }
        )


def test_create_parser_falls_back_to_stub_when_fixture_is_available(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("PADDLEOCR_API_TOKEN", raising=False)

    parser = create_parser(
        {
            "provider": "paddleocr_vl",
            "token_env_var": "PADDLEOCR_API_TOKEN",
        },
        fixture_path=Path("tests/fixtures/sample_prospectus.txt"),
    )

    assert isinstance(parser, ApiStubParser)


def test_create_parser_returns_paddle_parser_when_token_present(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")

    parser = create_parser(
        {
            "provider": "paddleocr_vl",
            "token_env_var": "PADDLEOCR_API_TOKEN",
            "poll_interval_seconds": 0,
        }
    )

    assert isinstance(parser, PaddleOCRVLParser)
