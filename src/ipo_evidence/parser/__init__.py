from __future__ import annotations

import os
from pathlib import Path

from ipo_evidence.parser.api_stub import ApiStubParser
from ipo_evidence.parser.paddleocr_vl import PaddleOCRVLParser


def create_parser(config: dict, fixture_path: Path | None = None):
    provider = config.get("provider", "api_stub")
    if provider == "api_stub":
        if fixture_path is None:
            raise RuntimeError("fixture_path is required for api_stub parser")
        return ApiStubParser(fixture_path=fixture_path)
    if provider == "paddleocr_vl":
        token_env_var = config.get("token_env_var", "PADDLEOCR_API_TOKEN")
        if not os.getenv(token_env_var):
            if fixture_path is not None:
                return ApiStubParser(fixture_path=fixture_path)
            raise RuntimeError(
                f"Missing required parser token in environment variable: {token_env_var}"
            )
        return PaddleOCRVLParser(
            job_url=config.get("job_url", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"),
            model=config.get("model", "PaddleOCR-VL-1.6"),
            token_env_var=token_env_var,
            optional_payload=config.get("optional_payload", {}),
            poll_interval_seconds=int(config.get("poll_interval_seconds", 5)),
            poll_timeout_seconds=int(config.get("poll_timeout_seconds", 600)),
        )
    raise ValueError(f"Unsupported parser provider: {provider}")


__all__ = ["ApiStubParser", "PaddleOCRVLParser", "create_parser"]
