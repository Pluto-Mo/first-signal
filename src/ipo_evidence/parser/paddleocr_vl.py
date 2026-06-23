from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

from ipo_evidence.models import Block
from ipo_evidence.parser.base import ParserOutput


class PaddleOCRVLParser:
    def __init__(
        self,
        job_url: str,
        model: str,
        token_env_var: str,
        optional_payload: dict,
        poll_interval_seconds: int = 5,
        poll_timeout_seconds: int = 600,
    ):
        self.job_url = job_url
        self.model = model
        self.token_env_var = token_env_var
        self.optional_payload = optional_payload
        self.poll_interval_seconds = poll_interval_seconds
        self.poll_timeout_seconds = poll_timeout_seconds

    def _token(self) -> str:
        token = os.getenv(self.token_env_var)
        if not token:
            raise RuntimeError(
                f"Missing required parser token in environment variable: {self.token_env_var}"
            )
        return token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"bearer {self._token()}"}

    def _submit_job(self, pdf_path: Path) -> str:
        data = {
            "model": self.model,
            "optionalPayload": json.dumps(self.optional_payload),
        }
        with pdf_path.open("rb") as file_handle:
            response = requests.post(
                self.job_url,
                headers=self._headers(),
                data=data,
                files={"file": file_handle},
                timeout=120,
            )
        response.raise_for_status()
        payload = response.json()
        return payload["data"]["jobId"]

    def _poll_until_done(self, job_id: str) -> dict:
        deadline = time.time() + self.poll_timeout_seconds
        while time.time() < deadline:
            response = requests.get(
                f"{self.job_url}/{job_id}",
                headers=self._headers(),
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()["data"]
            state = payload["state"]
            if state == "done":
                return payload
            if state == "failed":
                error_msg = payload.get("errorMsg", "unknown error")
                raise RuntimeError(f"PaddleOCR job failed: {error_msg}")
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"PaddleOCR job polling timed out for job_id={job_id}")

    def _download_jsonl_lines(self, json_url: str) -> list[dict]:
        response = requests.get(json_url, timeout=120)
        response.raise_for_status()
        lines: list[dict] = []
        for raw_line in response.text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lines.append(json.loads(line))
        return lines

    def _extract_markdown_entries(self, lines: list[dict]) -> list[dict]:
        entries: list[dict] = []
        for page_index, line in enumerate(lines, start=1):
            result = line.get("result", {})
            for layout_index, layout in enumerate(result.get("layoutParsingResults", []), start=1):
                markdown = layout.get("markdown", {})
                text = markdown.get("text", "").strip()
                if not text:
                    continue
                entries.append(
                    {
                        "page_number": page_index,
                        "layout_index": layout_index,
                        "text": text,
                    }
                )
        return entries

    def _blocks_from_markdown_entries(self, entries: list[dict]) -> list[Block]:
        blocks: list[Block] = []
        block_number = 1
        for entry in entries:
            for paragraph in [part.strip() for part in entry["text"].split("\n\n") if part.strip()]:
                blocks.append(
                    Block(
                        block_id=f"B-{block_number:06d}",
                        page_number=entry["page_number"],
                        text=paragraph,
                        section_path=[],
                    )
                )
                block_number += 1
        return blocks

    def _company_name_from_markdown(self, markdown: str) -> str:
        lines = [line.strip().lstrip("#").strip() for line in markdown.splitlines() if line.strip()]
        company_pattern = re.compile(
            r"^[\u4e00-\u9fffA-Za-z0-9（）()\-·\s]{2,}(?:股份有限公司|有限责任公司|有限公司)$"
        )
        for candidate in lines:
            if company_pattern.match(candidate):
                return candidate

        first_line = lines[0] if lines else ""
        candidate = first_line
        for suffix in ("招股说明书", "招股书"):
            if candidate.endswith(suffix):
                return candidate[: -len(suffix)].strip() or "unknown_company"
        return candidate or "unknown_company"

    def parse(self, pdf_path: Path) -> ParserOutput:
        job_id = self._submit_job(pdf_path)
        job_payload = self._poll_until_done(job_id)
        json_url = job_payload["resultUrl"]["jsonUrl"]
        lines = self._download_jsonl_lines(json_url)
        markdown_entries = self._extract_markdown_entries(lines)
        markdown = "\n\n".join(entry["text"] for entry in markdown_entries).strip() + "\n"
        blocks = self._blocks_from_markdown_entries(markdown_entries)
        company_name = self._company_name_from_markdown(markdown)
        parse_report = {
            "provider": "paddleocr_vl",
            "source_file": pdf_path.name,
            "quality_status": "safe_to_use" if blocks else "manual_review",
            "page_count": len({block.page_number for block in blocks}),
            "block_count": len(blocks),
            "raw_table_count": 0,
            "job_id": job_id,
            "result_json_url": json_url,
            "company_name": company_name,
        }
        raw_artifacts = {
            "job_meta": {
                "job_id": job_id,
                "state": job_payload.get("state"),
                "extract_progress": job_payload.get("extractProgress", {}),
                "result_url": job_payload.get("resultUrl", {}),
            },
            "raw_jsonl": lines,
        }
        return ParserOutput(
            markdown=markdown,
            blocks=blocks,
            raw_tables=[],
            parse_report=parse_report,
            raw_artifacts=raw_artifacts,
        )
