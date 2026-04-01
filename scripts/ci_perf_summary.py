#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from perf_data import (
    benchmarks_by_name,
    branch_relative_json_path,
    build_run_summary,
    compare_rows,
    format_comparison,
    summary_metadata,
    tracked_ref_relative_json_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("perf_results_dir", help="Directory containing raw perf result JSON files")
    parser.add_argument("--ref-name", default=os.getenv("GITHUB_REF_NAME", "current"), help="Current git ref name")
    parser.add_argument(
        "--published-root",
        help="Local directory containing published perf JSON under perf/",
    )
    parser.add_argument(
        "--gh-pages-ref",
        help="Git ref to read published perf JSON from, for example origin/gh-pages",
    )
    return parser.parse_args()


def _load_summary_from_git(git_ref: str, relative_path: Path) -> dict[str, Any] | None:
    completed = subprocess.run(
        ["git", "show", f"{git_ref}:{relative_path.as_posix()}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def _load_summary_from_root(published_root: Path, relative_path: Path) -> dict[str, Any] | None:
    target = published_root / relative_path
    if not target.is_file():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def load_published_summary(
    relative_path: Path,
    published_root: Path | None = None,
    gh_pages_ref: str | None = None,
) -> dict[str, Any] | None:
    if published_root is not None:
        return _load_summary_from_root(published_root, relative_path)
    if gh_pages_ref:
        return _load_summary_from_git(gh_pages_ref, relative_path)
    return None


def _render_reference_line(label: str, summary: dict[str, Any] | None) -> str:
    if not summary:
        return f"- {label}: n/a"
    metadata = summary_metadata(summary)
    suffix = f" ({metadata['published_at']})" if metadata.get("published_at") else ""
    return f"- {label}: `{metadata['short_sha']}`{suffix}"


def render_summary_markdown(
    current_summary: dict[str, Any],
    previous_branch_summary: dict[str, Any] | None,
    main_summary: dict[str, Any] | None,
    pre_release_summary: dict[str, Any] | None,
) -> str:
    rows = []
    previous_rows = benchmarks_by_name(previous_branch_summary)
    main_rows = benchmarks_by_name(main_summary)
    pre_release_rows = benchmarks_by_name(pre_release_summary)

    for row in current_summary.get("benchmarks", []):
        notes = "; ".join(row.get("notes", []))
        rows.append(
            "| {name} | {current} | {previous} | {main} | {pre_release} | {complete} | {rx_errors} | {notes} |".format(
                name=row["name"],
                current=row.get("rate_display", ""),
                previous=format_comparison(compare_rows(row, previous_rows.get(row["name"]))),
                main=format_comparison(compare_rows(row, main_rows.get(row["name"]))),
                pre_release=format_comparison(compare_rows(row, pre_release_rows.get(row["name"]))),
                complete=row.get("complete"),
                rx_errors=row.get("rx_errors"),
                notes=notes,
            )
        )

    current_meta = summary_metadata(current_summary)
    branch_label = current_meta["ref_name"] or "current branch"

    lines = [
        "## Performance Results",
        "",
        f"Current ref: `{branch_label}` @ `{current_meta['short_sha'] or 'working-tree'}`",
        "",
        "Published comparisons:",
        _render_reference_line(f"previous `{branch_label}` run", previous_branch_summary),
        _render_reference_line("`main` baseline", main_summary),
        _render_reference_line("`pre-release` baseline", pre_release_summary),
        "",
        "| Benchmark | Current | Vs Previous Branch | Vs Main | Vs Pre-release | Complete | Rx Errors | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *rows,
    ]

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    result_dir = Path(args.perf_results_dir)
    files = sorted(result_dir.glob("*.json"))

    if not files:
        print("## Performance Results\n\nNo perf result files were found.")
        return 0

    run_url = ""
    if os.getenv("GITHUB_SERVER_URL") and os.getenv("GITHUB_REPOSITORY") and os.getenv("GITHUB_RUN_ID"):
        run_url = "/".join(
            [
                os.environ["GITHUB_SERVER_URL"].rstrip("/"),
                os.environ["GITHUB_REPOSITORY"],
                "actions",
                "runs",
                os.environ["GITHUB_RUN_ID"],
            ]
        )

    current_summary = build_run_summary(
        result_dir=result_dir,
        ref_name=args.ref_name,
        sha=os.getenv("GITHUB_SHA", ""),
        run_id=os.getenv("GITHUB_RUN_ID", ""),
        run_url=run_url,
    )

    published_root = Path(args.published_root).resolve() if args.published_root else None
    previous_branch_summary = load_published_summary(
        branch_relative_json_path(args.ref_name),
        published_root=published_root,
        gh_pages_ref=args.gh_pages_ref,
    )
    main_summary = load_published_summary(
        tracked_ref_relative_json_path("main"),
        published_root=published_root,
        gh_pages_ref=args.gh_pages_ref,
    )
    pre_release_summary = load_published_summary(
        tracked_ref_relative_json_path("pre-release"),
        published_root=published_root,
        gh_pages_ref=args.gh_pages_ref,
    )

    print(
        render_summary_markdown(
            current_summary=current_summary,
            previous_branch_summary=previous_branch_summary,
            main_summary=main_summary,
            pre_release_summary=pre_release_summary,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
