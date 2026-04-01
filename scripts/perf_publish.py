#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Performance Publisher
# ----------------------------------------------------------------------------
# This file is part of the rogue software package. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software package, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

from perf_data import (
    TRACKED_BASELINE_REFS,
    benchmarks_by_name,
    branch_history_relative_json_path,
    branch_relative_json_path,
    build_run_summary,
    compare_rows,
    format_comparison,
    perf_index_relative_json_path,
    read_json,
    slugify_ref_name,
    summary_metadata,
    tracked_ref_relative_json_path,
    url_join,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True, help="Directory containing perf-results JSON files")
    parser.add_argument("--output-root", required=True, help="Target gh-pages worktree root")
    parser.add_argument("--site-root", required=True, help="Public site root, for example /rogue")
    parser.add_argument("--ref-name", required=True, help="Git branch name for the perf run")
    parser.add_argument("--sha", required=True, help="Git commit SHA for the perf run")
    parser.add_argument("--run-id", help="GitHub Actions run id")
    parser.add_argument("--run-url", help="GitHub Actions run URL")
    parser.add_argument(
        "--max-branch-history",
        type=int,
        default=20,
        help="Maximum number of branch history entries to retain",
    )
    return parser.parse_args()


def _load_summary(path: Path) -> dict[str, Any]:
    return read_json(path)


def _summary_link(site_root: str, relative_path: Path) -> str:
    return url_join(site_root, *relative_path.parts)


def _summary_entry(site_root: str, relative_path: Path, summary: dict[str, Any]) -> dict[str, str]:
    metadata = summary_metadata(summary)
    return {
        "ref_name": metadata["ref_name"],
        "sha": metadata["sha"],
        "short_sha": metadata["short_sha"],
        "published_at": metadata["published_at"],
        "run_url": metadata["run_url"],
        "summary_url": _summary_link(site_root, relative_path),
    }


def _collect_branch_history(branch_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    history_dir = branch_dir / "history"
    if not history_dir.is_dir():
        return []

    entries = [(path, _load_summary(path)) for path in history_dir.glob("*.json")]
    entries.sort(
        key=lambda item: (
            item[1].get("published_at", ""),
            item[1].get("sha", ""),
        ),
        reverse=True,
    )
    return entries


def _prune_branch_history(branch_dir: Path, max_entries: int) -> list[tuple[Path, dict[str, Any]]]:
    entries = _collect_branch_history(branch_dir)
    for path, _summary in entries[max_entries:]:
        path.unlink(missing_ok=True)
    return entries[:max_entries]


def _write_branch_index(site_root: str, ref_name: str, branch_dir: Path, history_entries: list[tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    latest_summary = history_entries[0][1] if history_entries else None
    payload = {
        "ref_name": ref_name,
        "ref_slug": slugify_ref_name(ref_name),
        "latest_url": _summary_link(site_root, branch_relative_json_path(ref_name)),
        "history": [
            _summary_entry(site_root, path.relative_to(branch_dir.parents[2]), summary)
            for path, summary in history_entries
        ],
    }
    if latest_summary:
        payload["latest"] = _summary_entry(site_root, branch_relative_json_path(ref_name), latest_summary)
    write_json(branch_dir / "index.json", payload)
    return payload


def _load_tracked_refs(output_root: Path) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for ref_name in TRACKED_BASELINE_REFS:
        path = output_root / tracked_ref_relative_json_path(ref_name)
        if path.is_file():
            refs[ref_name] = _load_summary(path)
    return refs


def _collect_branch_manifests(site_root: str, output_root: Path) -> list[dict[str, Any]]:
    branches_root = output_root / "perf" / "branches"
    manifests: list[dict[str, Any]] = []

    if not branches_root.is_dir():
        return manifests

    for branch_dir in branches_root.iterdir():
        if not branch_dir.is_dir():
            continue
        index_path = branch_dir / "index.json"
        latest_path = branch_dir / "latest.json"
        if not index_path.is_file() or not latest_path.is_file():
            continue

        manifest = _load_summary(index_path)
        latest_summary = _load_summary(latest_path)
        history_entries = _collect_branch_history(branch_dir)
        manifests.append(
            {
                "manifest": manifest,
                "latest_summary": latest_summary,
                "history_summaries": [summary for _path, summary in history_entries],
                "latest_url": _summary_link(site_root, latest_path.relative_to(output_root)),
            }
        )

    def sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
        ref_name = item["manifest"].get("ref_name", "")
        if ref_name == "main":
            return (0, "", "")
        if ref_name == "pre-release":
            return (1, "", "")
        latest = item["latest_summary"]
        return (2, latest.get("published_at", ""), ref_name)

    manifests.sort(key=sort_key, reverse=False)
    tail = manifests[2:]
    tail.sort(key=lambda item: item["latest_summary"].get("published_at", ""), reverse=True)
    return manifests[:2] + tail


def _render_history_list(history: list[dict[str, Any]]) -> str:
    if not history:
        return "<p>No history published yet.</p>"

    items = []
    for entry in history[:8]:
        run_link = ""
        if entry.get("run_url"):
            run_link = f' <a href="{html.escape(entry["run_url"])}">run</a>'
        items.append(
            "<li>"
            f'<a href="{html.escape(entry["summary_url"])}"><code>{html.escape(entry["short_sha"])}</code></a>'
            f" <span>{html.escape(entry['published_at'])}</span>{run_link}"
            "</li>"
        )
    return "<ul>" + "".join(items) + "</ul>"


def _render_branch_table(current: dict[str, Any], previous: dict[str, Any] | None, refs: dict[str, dict[str, Any]]) -> str:
    current_rows = current.get("benchmarks", [])
    previous_rows = benchmarks_by_name(previous)
    main_rows = benchmarks_by_name(refs.get("main"))
    pre_release_rows = benchmarks_by_name(refs.get("pre-release"))
    ref_name = current.get("ref_name", "")

    rows = []
    for row in current_rows:
        previous_text = format_comparison(compare_rows(row, previous_rows.get(row["name"])))
        if ref_name == "main":
            main_text = "current ref"
        else:
            main_text = format_comparison(compare_rows(row, main_rows.get(row["name"])))

        if ref_name == "pre-release":
            pre_release_text = "current ref"
        else:
            pre_release_text = format_comparison(compare_rows(row, pre_release_rows.get(row["name"])))

        notes = "; ".join(row.get("notes", []))
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(row['name'])}</code></td>"
            f"<td>{html.escape(row.get('rate_display', ''))}</td>"
            f"<td>{html.escape(previous_text)}</td>"
            f"<td>{html.escape(main_text)}</td>"
            f"<td>{html.escape(pre_release_text)}</td>"
            f"<td>{html.escape(str(row.get('complete')))}</td>"
            f"<td>{html.escape(str(row.get('rx_errors')))}</td>"
            f"<td>{html.escape(notes)}</td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr>"
        "<th>Benchmark</th><th>Current</th><th>Vs Previous</th><th>Vs Main</th>"
        "<th>Vs Pre-release</th><th>Complete</th><th>Rx Errors</th><th>Notes</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_dashboard(site_root: str, refs: dict[str, dict[str, Any]], branches: list[dict[str, Any]]) -> str:
    baseline_items = []
    for ref_name in TRACKED_BASELINE_REFS:
        summary = refs.get(ref_name)
        if not summary:
            baseline_items.append(f"<li><strong>{html.escape(ref_name)}</strong>: not published yet</li>")
            continue
        meta = summary_metadata(summary)
        baseline_items.append(
            "<li>"
            f"<strong>{html.escape(ref_name)}</strong>: "
            f'<a href="{html.escape(_summary_link(site_root, tracked_ref_relative_json_path(ref_name)))}">'
            f"<code>{html.escape(meta['short_sha'])}</code></a> "
            f"<span>{html.escape(meta['published_at'])}</span>"
            "</li>"
        )

    branch_sections = []
    for branch in branches:
        manifest = branch["manifest"]
        latest = branch["latest_summary"]
        history = manifest.get("history", [])
        previous_summary = branch["history_summaries"][1] if len(branch["history_summaries"]) > 1 else None
        meta = summary_metadata(latest)
        run_link = ""
        if meta.get("run_url"):
            run_link = f' <a href="{html.escape(meta["run_url"])}">Open workflow run</a>'

        branch_sections.append(
            "<section class=\"branch\">"
            f"<h2>{html.escape(manifest['ref_name'])}</h2>"
            "<p class=\"meta\">"
            f"Latest: <a href=\"{html.escape(branch['latest_url'])}\"><code>{html.escape(meta['short_sha'])}</code></a> "
            f"<span>{html.escape(meta['published_at'])}</span>{run_link}"
            "</p>"
            "<h3>Recent History</h3>"
            f"{_render_history_list(history)}"
            "<h3>Benchmark Comparisons</h3>"
            f"{_render_branch_table(latest, previous_summary, refs)}"
            "</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rogue Performance Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fb;
      --card: #ffffff;
      --border: #d8dee9;
      --text: #1c2533;
      --muted: #5c6b80;
      --link: #005a9c;
      --code: #eef3fb;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }}
    main {{
      max-width: 84rem;
      margin: 0 auto;
      padding: 2.5rem 1.5rem 3rem;
    }}
    h1 {{
      margin-bottom: 0.25rem;
    }}
    p.lead {{
      color: var(--muted);
      margin-top: 0;
    }}
    section {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      padding: 1.25rem 1.5rem;
      margin-top: 1rem;
    }}
    section.branch {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.75rem;
      font-size: 0.95rem;
    }}
    th, td {{
      border-top: 1px solid var(--border);
      padding: 0.65rem 0.5rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      font-size: 0.85rem;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    a {{
      color: var(--link);
    }}
    code {{
      background: var(--code);
      padding: 0.1rem 0.3rem;
      border-radius: 0.25rem;
    }}
    .meta {{
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <main>
    <h1>Rogue Performance Dashboard</h1>
    <p class="lead">
      Published branch history with comparisons against previous branch runs,
      <code>main</code>, and <code>pre-release</code>.
    </p>
    <section>
      <h2>Current Baselines</h2>
      <ul>
        {''.join(baseline_items)}
      </ul>
    </section>
    {''.join(branch_sections) if branch_sections else '<section><p>No perf data published yet.</p></section>'}
  </main>
</body>
</html>
"""


def publish_perf_data(
    results_dir: Path,
    output_root: Path,
    site_root: str,
    ref_name: str,
    sha: str,
    run_id: str | None = None,
    run_url: str | None = None,
    max_branch_history: int = 20,
) -> dict[str, Any]:
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Perf results directory not found: {results_dir}")

    summary = build_run_summary(results_dir, ref_name, sha, run_id=run_id, run_url=run_url)
    branch_dir = output_root / "perf" / "branches" / slugify_ref_name(ref_name)
    history_path = output_root / branch_history_relative_json_path(ref_name, sha)
    latest_path = output_root / branch_relative_json_path(ref_name)

    write_json(history_path, summary)
    write_json(latest_path, summary)

    if ref_name in TRACKED_BASELINE_REFS:
        write_json(output_root / tracked_ref_relative_json_path(ref_name), summary)

    history_entries = _prune_branch_history(branch_dir, max_branch_history)
    _write_branch_index(site_root, ref_name, branch_dir, history_entries)

    refs = _load_tracked_refs(output_root)
    branches = _collect_branch_manifests(site_root, output_root)
    perf_index = {
        "generated_at": utc_now_iso(),
        "site_root": site_root,
        "refs": {
            name: _summary_entry(site_root, tracked_ref_relative_json_path(name), summary)
            for name, summary in refs.items()
        },
        "branches": [branch["manifest"] for branch in branches],
    }
    write_json(output_root / perf_index_relative_json_path(), perf_index)

    index_html = render_dashboard(site_root, refs, branches)
    index_path = output_root / "perf" / "index.html"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index_html, encoding="utf-8")

    return summary


def main() -> int:
    args = parse_args()
    publish_perf_data(
        results_dir=Path(args.results_dir).resolve(),
        output_root=Path(args.output_root).resolve(),
        site_root=args.site_root,
        ref_name=args.ref_name,
        sha=args.sha,
        run_id=args.run_id,
        run_url=args.run_url,
        max_branch_history=args.max_branch_history,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
