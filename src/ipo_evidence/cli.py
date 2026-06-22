from __future__ import annotations

import argparse


def _placeholder(command: str) -> int:
    print(f"{command} is planned for a later MVP implementation task.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ipo-evidence",
        description="Local A-share prospectus evidence reader.",
    )
    subparsers = parser.add_subparsers(dest="command")

    scan_inbox = subparsers.add_parser(
        "scan-inbox",
        help="Scan local PDF inputs in data/inbox.",
    )
    scan_inbox.set_defaults(handler=lambda _args: _placeholder("scan-inbox"))

    run = subparsers.add_parser(
        "run",
        help="Run the local evidence pipeline.",
    )
    run.add_argument("--limit", type=int, default=None, help="Limit the number of documents.")
    run.set_defaults(handler=lambda _args: _placeholder("run"))

    generate_report = subparsers.add_parser(
        "generate-report",
        help="Generate a report for a document package.",
    )
    generate_report.add_argument("--doc-id", required=True, help="Document package id.")
    generate_report.set_defaults(handler=lambda _args: _placeholder("generate-report"))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
