# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ci_perf_summary
import perf_data
import perf_publish


def _write_result(result_dir: Path, name: str, **payload) -> None:
    result_dir.mkdir(parents=True, exist_ok=True)
    path = result_dir / f"{name}.json"
    path.write_text(json.dumps({"name": name, **payload}, indent=2) + "\n", encoding="utf-8")


def test_build_run_summary_normalizes_perf_metrics(tmp_path):
    result_dir = tmp_path / "perf-results"
    _write_result(
        result_dir,
        "variable_rate_perf_remoteSetRate",
        avg_ns=123.456,
        rate_hz=8100,
        threshold_pass=True,
        cycles=111.0,
    )
    _write_result(
        result_dir,
        "stream_bridge_perf",
        throughput_mb_s=456.789,
        frames_sent=10,
        frames_received=10,
        elapsed_sec=1.23,
        rx_errors=0,
        drain_complete=True,
    )

    summary = perf_data.build_run_summary(result_dir, "feature/perf", "abcdef123456")
    rows = perf_data.benchmarks_by_name(summary)

    variable = rows["variable_rate_perf_remoteSetRate"]
    assert variable["primary_metric"]["key"] == "avg_ns"
    assert variable["primary_metric"]["better"] == "lower"
    assert variable["rate_display"] == "123.456 ns/op, 8100 ops/s"
    assert "cycles=111.000" in variable["notes"]

    bridge = rows["stream_bridge_perf"]
    assert bridge["primary_metric"]["key"] == "throughput_mb_s"
    assert bridge["primary_metric"]["better"] == "higher"
    assert bridge["rate_display"] == "456.789 MB/s"
    assert "frames=10/10" in bridge["notes"]

    assert summary["ref_slug"] == "feature_perf"
    assert summary["short_sha"] == "abcdef1"


def test_perf_publish_creates_branch_history_refs_and_dashboard(tmp_path):
    output_root = tmp_path / "gh-pages"

    main_results = tmp_path / "main-results"
    _write_result(main_results, "stream_bridge_perf", throughput_mb_s=500.0, frames_sent=10, frames_received=10)
    perf_publish.publish_perf_data(
        results_dir=main_results,
        output_root=output_root,
        site_root="/rogue",
        ref_name="main",
        sha="1111111abcdef",
        run_id="101",
        run_url="https://example.invalid/runs/101",
    )

    pre_results = tmp_path / "pre-results"
    _write_result(pre_results, "stream_bridge_perf", throughput_mb_s=520.0, frames_sent=10, frames_received=10)
    perf_publish.publish_perf_data(
        results_dir=pre_results,
        output_root=output_root,
        site_root="/rogue",
        ref_name="pre-release",
        sha="2222222abcdef",
        run_id="102",
        run_url="https://example.invalid/runs/102",
    )

    feature_results_1 = tmp_path / "feature-results-1"
    _write_result(feature_results_1, "stream_bridge_perf", throughput_mb_s=450.0, frames_sent=10, frames_received=10)
    perf_publish.publish_perf_data(
        results_dir=feature_results_1,
        output_root=output_root,
        site_root="/rogue",
        ref_name="feature/perf",
        sha="3333333abcdef",
        run_id="103",
        run_url="https://example.invalid/runs/103",
    )

    feature_results_2 = tmp_path / "feature-results-2"
    _write_result(feature_results_2, "stream_bridge_perf", throughput_mb_s=470.0, frames_sent=10, frames_received=10)
    perf_publish.publish_perf_data(
        results_dir=feature_results_2,
        output_root=output_root,
        site_root="/rogue",
        ref_name="feature/perf",
        sha="4444444abcdef",
        run_id="104",
        run_url="https://example.invalid/runs/104",
    )

    latest_feature = json.loads(
        (output_root / "perf" / "branches" / "feature_perf" / "latest.json").read_text(encoding="utf-8")
    )
    assert latest_feature["short_sha"] == "4444444"

    branch_index = json.loads(
        (output_root / "perf" / "branches" / "feature_perf" / "index.json").read_text(encoding="utf-8")
    )
    assert [entry["short_sha"] for entry in branch_index["history"][:2]] == ["4444444", "3333333"]

    assert (output_root / "perf" / "refs" / "main" / "latest.json").is_file()
    assert (output_root / "perf" / "refs" / "pre-release" / "latest.json").is_file()

    dashboard = (output_root / "perf" / "index.html").read_text(encoding="utf-8")
    assert "feature/perf" in dashboard
    assert "Vs Main" in dashboard
    assert "Vs Pre-release" in dashboard


def test_ci_perf_summary_renders_branch_and_baseline_comparisons(tmp_path):
    published_root = tmp_path / "published"

    previous_results = tmp_path / "previous-results"
    _write_result(previous_results, "stream_bridge_perf", throughput_mb_s=450.0, frames_sent=10, frames_received=10)
    perf_publish.publish_perf_data(
        results_dir=previous_results,
        output_root=published_root,
        site_root="/rogue",
        ref_name="feature/perf",
        sha="5555555abcdef",
    )

    main_results = tmp_path / "main-results"
    _write_result(main_results, "stream_bridge_perf", throughput_mb_s=430.0, frames_sent=10, frames_received=10)
    perf_publish.publish_perf_data(
        results_dir=main_results,
        output_root=published_root,
        site_root="/rogue",
        ref_name="main",
        sha="6666666abcdef",
    )

    pre_results = tmp_path / "pre-results"
    _write_result(pre_results, "stream_bridge_perf", throughput_mb_s=440.0, frames_sent=10, frames_received=10)
    perf_publish.publish_perf_data(
        results_dir=pre_results,
        output_root=published_root,
        site_root="/rogue",
        ref_name="pre-release",
        sha="7777777abcdef",
    )

    current_results = tmp_path / "current-results"
    _write_result(current_results, "stream_bridge_perf", throughput_mb_s=470.0, frames_sent=10, frames_received=10)
    current_summary = perf_data.build_run_summary(current_results, "feature/perf", "8888888abcdef")

    markdown = ci_perf_summary.render_summary_markdown(
        current_summary=current_summary,
        previous_branch_summary=ci_perf_summary.load_published_summary(
            perf_data.branch_relative_json_path("feature/perf"),
            published_root=published_root,
        ),
        main_summary=ci_perf_summary.load_published_summary(
            perf_data.tracked_ref_relative_json_path("main"),
            published_root=published_root,
        ),
        pre_release_summary=ci_perf_summary.load_published_summary(
            perf_data.tracked_ref_relative_json_path("pre-release"),
            published_root=published_root,
        ),
    )

    assert "Current ref: `feature/perf` @ `8888888`" in markdown
    assert "previous `feature/perf` run" in markdown
    assert "Vs Main" in markdown
    assert "improved" in markdown
