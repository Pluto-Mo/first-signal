from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from ipo_evidence.parser.paddleocr_vl import PaddleOCRVLParser


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or (json.dumps(payload, ensure_ascii=False) if payload is not None else "")

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("payload is not set")
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


def test_paddleocr_vl_parser_normalizes_markdown_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nsample")
    monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")

    job_states = [
        FakeResponse(200, {"data": {"state": "pending"}}),
        FakeResponse(
            200,
            {
                "data": {
                    "state": "done",
                    "extractProgress": {
                        "extractedPages": 1,
                        "startTime": "2026-06-23T10:00:00Z",
                        "endTime": "2026-06-23T10:00:10Z",
                    },
                    "resultUrl": {"jsonUrl": "https://example.com/result.jsonl"},
                }
            },
        ),
    ]

    jsonl_text = json.dumps(
        {
            "result": {
                "layoutParsingResults": [
                    {
                        "markdown": {
                            "text": (
                                "# 测试股份有限公司招股说明书\n\n"
                                "## 第一节 发行人基本情况\n\n"
                                "公司主要从事智能硬件产品的研发、生产和销售。"
                            ),
                            "images": {},
                        },
                        "outputImages": {},
                    }
                ]
            }
        },
        ensure_ascii=False,
    )

    def fake_post(*_args, **_kwargs) -> FakeResponse:
        return FakeResponse(200, {"data": {"jobId": "job-123"}})

    def fake_get(url: str, *_args, **_kwargs) -> FakeResponse:
        if url.endswith("/job-123"):
            return job_states.pop(0)
        if url == "https://example.com/result.jsonl":
            return FakeResponse(200, text=jsonl_text)
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("ipo_evidence.parser.paddleocr_vl.requests.post", fake_post)
    monkeypatch.setattr("ipo_evidence.parser.paddleocr_vl.requests.get", fake_get)

    parser = PaddleOCRVLParser(
        job_url="https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        model="PaddleOCR-VL-1.6",
        token_env_var="PADDLEOCR_API_TOKEN",
        optional_payload={},
        poll_interval_seconds=0,
        poll_timeout_seconds=1,
    )
    output = parser.parse(pdf_path)

    assert output.markdown.startswith("# 测试股份有限公司招股说明书")
    assert output.blocks[0].block_id == "B-000001"
    assert output.blocks[0].page_number == 1
    assert output.parse_report["provider"] == "paddleocr_vl"
    assert output.parse_report["company_name"] == "测试股份有限公司"
    assert output.raw_artifacts["job_meta"]["job_id"] == "job-123"
    assert len(output.raw_artifacts["raw_jsonl"]) == 1


def test_paddleocr_vl_parser_prefers_actual_company_name_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nsample")
    monkeypatch.setenv("PADDLEOCR_API_TOKEN", "test-token")

    def fake_post(*_args, **_kwargs) -> FakeResponse:
        return FakeResponse(200, {"data": {"jobId": "job-456"}})

    def fake_get(url: str, *_args, **_kwargs) -> FakeResponse:
        if url.endswith("/job-456"):
            return FakeResponse(
                200,
                {
                    "data": {
                        "state": "done",
                        "extractProgress": {"extractedPages": 1},
                        "resultUrl": {"jsonUrl": "https://example.com/result-company.jsonl"},
                    }
                },
            )
        if url == "https://example.com/result-company.jsonl":
            return FakeResponse(
                200,
                text=json.dumps(
                    {
                        "result": {
                            "layoutParsingResults": [
                                {
                                    "markdown": {
                                        "text": (
                                            "本次发行股票拟在科创板上市，投资者应审慎作出投资决定。\n\n"
                                            "思必驰科技股份有限公司\n\n"
                                            "# 首次公开发行股票并在科创板上市 招股说明书"
                                        ),
                                        "images": {},
                                    },
                                    "outputImages": {},
                                }
                            ]
                        }
                    },
                    ensure_ascii=False,
                ),
            )
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("ipo_evidence.parser.paddleocr_vl.requests.post", fake_post)
    monkeypatch.setattr("ipo_evidence.parser.paddleocr_vl.requests.get", fake_get)

    parser = PaddleOCRVLParser(
        job_url="https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        model="PaddleOCR-VL-1.6",
        token_env_var="PADDLEOCR_API_TOKEN",
        optional_payload={},
        poll_interval_seconds=0,
        poll_timeout_seconds=1,
    )

    output = parser.parse(pdf_path)

    assert output.parse_report["company_name"] == "思必驰科技股份有限公司"
