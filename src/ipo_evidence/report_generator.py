from __future__ import annotations

from ipo_evidence.models import EvidencePacket


def generate_report(company_name: str, packet: EvidencePacket) -> str:
    lines = [
        f"# {company_name}招股书解读",
        "",
        "## 1. 处理结论",
        "",
        "当前报告由本地证据包生成，适合进行第一轮人工复核。",
        "",
        "## 2. 关于公司",
        "",
    ]
    for index, item in enumerate(packet.items, start=1):
        citation_id = f"C-{index:03d}"
        lines.append(f"- {item.claim_summary}[{citation_id}]")
    lines.extend(
        [
            "",
            "## 3. 后续跟踪问题",
            "",
            "- 需要继续核查客户集中度、募投项目合理性和风险因素。",
        ]
    )
    return "\n".join(lines) + "\n"
