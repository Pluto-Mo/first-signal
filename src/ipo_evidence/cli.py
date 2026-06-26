from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from ipo_evidence.ingest import scan_inbox
from ipo_evidence.paths import docs_dir, inbox_dir, repo_root
from ipo_evidence.pipeline import regenerate_report, run_one


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ipo-evidence",
        description="Local A-share prospectus evidence reader.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_inbox = subparsers.add_parser(
        "scan-inbox",
        help="Scan local PDF inputs in data/inbox.",
    )
    scan_inbox.set_defaults(handler=handle_scan_inbox)

    run = subparsers.add_parser(
        "run",
        help="Run the local evidence pipeline.",
    )
    run.add_argument(
        "--limit",
        type=_positive_int,
        default=3,
        help="Limit the number of documents.",
    )
    run.set_defaults(handler=handle_run)

    generate_report = subparsers.add_parser(
        "generate-report",
        help="Generate a report for a document package.",
    )
    generate_report.add_argument("--doc-id", required=True, help="Document package id.")
    generate_report.set_defaults(handler=handle_generate_report)

    return parser


def _find_pdfs(directory: Path) -> list[Path]:
    return sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"
    )


def handle_scan_inbox(_args: argparse.Namespace) -> int:
    manifests = scan_inbox(inbox_dir(), docs_dir())
    print(f"scanned={len(manifests)}")
    return 0


def handle_run(args: argparse.Namespace) -> int:
    fixture = repo_root() / "tests" / "fixtures" / "sample_prospectus.txt"
    pdfs = _find_pdfs(inbox_dir())[: args.limit]
    for pdf in pdfs:
        doc_id = run_one(pdf, docs_dir(), fixture)
        print(f"processed={doc_id}")
    return 0


def handle_generate_report(args: argparse.Namespace) -> int:
    regenerate_report(args.doc_id, docs_dir())
    print(f"reported={args.doc_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(repo_root() / ".env")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
