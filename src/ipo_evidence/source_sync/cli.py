from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from ipo_evidence.config import load_yaml
from ipo_evidence.paths import repo_root
from ipo_evidence.source_sync.client import CNInfoClient
from ipo_evidence.source_sync.downloader import SyncDownloader
from ipo_evidence.source_sync.service import run_sync
from ipo_evidence.source_sync.state import append_jsonl_record, load_sync_state, save_sync_state


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ipo-evidence-source-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync = subparsers.add_parser("sync-a-share")
    sync.add_argument("--days", type=positive_int, default=7)
    sync.add_argument("--limit", type=positive_int, default=3)
    sync.set_defaults(handler=handle_sync_a_share)
    return parser


def handle_sync_a_share(args: argparse.Namespace) -> int:
    sync_config = load_yaml("configs/source_sync.yaml")
    filter_config = load_yaml("configs/filter_rules.yaml")
    cninfo_config = sync_config["cninfo"]
    paths_config = sync_config["paths"]
    repo = repo_root()
    state_dir = repo / paths_config["state_dir"]
    existing_state = load_sync_state(state_dir / "sync_state.json")
    downloader = SyncDownloader(repo / paths_config["inbox_dir"])
    client = CNInfoClient(
        prospectus_list_url=cninfo_config["prospectus_list_url"],
        announcement_search_url=cninfo_config["announcement_search_url"],
        user_agent=cninfo_config["user_agent"],
        referer=cninfo_config["referer"],
        request_interval_seconds=float(sync_config["throttle"]["request_interval_seconds"]),
    )
    summary = run_sync(
        client=client,
        filter_config=filter_config,
        days=args.days,
        limit=args.limit,
        downloader=downloader,
        processed_announcement_ids=set(existing_state.processed_announcement_ids),
    )
    timestamp = datetime.now().isoformat(timespec="seconds")
    for candidate in summary["candidates"]:
        append_jsonl_record(
            state_dir / "discovery_log.jsonl",
            candidate.model_dump(mode="json"),
        )
        decision = summary["decisions"][candidate.sync_id]
        if decision.decision.value != "allow":
            append_jsonl_record(
                state_dir / "filter_log.jsonl",
                {
                    "candidate": candidate.model_dump(mode="json"),
                    "result": decision.model_dump(mode="json"),
                    "restorable": True,
                    "logged_at": timestamp,
                },
            )
    for record in summary["downloads"]:
        append_jsonl_record(
            state_dir / "download_log.jsonl",
            {**record, "downloaded_at": timestamp},
        )
    processed_ids = list(existing_state.processed_announcement_ids)
    for record in summary["downloads"]:
        if record["announcement_id"] not in processed_ids:
            processed_ids.append(record["announcement_id"])
    save_sync_state(
        state_dir / "sync_state.json",
        {
            "last_successful_run_at": timestamp,
            "last_window_start": f"lookback:{args.days}",
            "processed_announcement_ids": processed_ids,
        },
    )
    print(
        f"downloaded={len(summary['downloads'])} "
        f"skipped_existing={len(summary['skipped_existing'])}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
