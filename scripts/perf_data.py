#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Performance Data Helpers
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

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
TRACKED_BASELINE_REFS = ("main", "pre-release")
COMPARISON_HIGHLIGHT_THRESHOLD_PERCENT = 5.0

# The published field distinguishing a multi-sample harness-produced record from a
# historical single-sample one. Permanent once published: see upgrade_summary().
SAMPLE_PROVENANCE_KEY = "sample_provenance"
SAMPLE_PROVENANCE_SINGLE_SAMPLE = "single-sample"
SAMPLE_PROVENANCE_MULTI_SAMPLE_CLEAN = "multi-sample-clean"
SAMPLE_PROVENANCE_VALUES = (SAMPLE_PROVENANCE_SINGLE_SAMPLE, SAMPLE_PROVENANCE_MULTI_SAMPLE_CLEAN)

# The in-memory-only gate-eligibility marking. Never enters a published record;
# upgrade_summary() is the sole place these are set.
GATE_ELIGIBLE_KEY = "gate_eligible"
GATE_ELIGIBLE_REASON_KEY = "gate_eligible_reason"
GATE_REASON_UPGRADED_FROM_SCHEMA_VERSION_1 = "upgraded-from-schema-version-1"
GATE_REASON_SINGLE_SAMPLE_PUBLISHED = "single-sample-published"
GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION = "unrecognized-schema-version"
# Distinct from GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION: this names a record whose
# schema_version was recognized but whose sample_provenance value was not.
GATE_REASON_UNRECOGNIZED_SAMPLE_PROVENANCE = "unrecognized-sample-provenance"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_site_root(site_root: str) -> str:
    site_root = site_root.strip()
    if not site_root or site_root == "/":
        return ""
    if not site_root.startswith("/"):
        site_root = f"/{site_root}"
    return site_root.rstrip("/")


def url_join(site_root: str, *parts: str, trailing_slash: bool = True) -> str:
    pieces = [normalize_site_root(site_root).strip("/")] if site_root else [""]
    pieces.extend(part.strip("/") for part in parts if part)
    path = "/".join(piece for piece in pieces if piece)
    if not path:
        return "/"
    return f"/{path}/" if trailing_slash else f"/{path}"


def slugify_ref_name(ref_name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", ref_name.strip())
    return slug or "unknown"


def short_sha(sha: str) -> str:
    return sha[:7] if sha else ""


def branch_relative_json_path(ref_name: str, filename: str = "latest.json") -> Path:
    return Path("perf") / "branches" / slugify_ref_name(ref_name) / filename


def branch_history_relative_json_path(ref_name: str, sha: str) -> Path:
    return Path("perf") / "branches" / slugify_ref_name(ref_name) / "history" / f"{sha}.json"


def branch_index_relative_json_path(ref_name: str) -> Path:
    return Path("perf") / "branches" / slugify_ref_name(ref_name) / "index.json"


def tracked_ref_relative_json_path(ref_name: str) -> Path:
    return Path("perf") / "refs" / ref_name / "latest.json"


def perf_index_relative_json_path() -> Path:
    return Path("perf") / "index.json"


def _fmt_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load_perf_results(result_dir: Path) -> list[dict[str, Any]]:
    return [read_json(path) for path in sorted(result_dir.glob("*.json"))]


def _metric_descriptor(data: dict[str, Any]) -> dict[str, Any] | None:
    if "avg_ns" in data:
        value = _coerce_float(data.get("avg_ns"))
        if value is None:
            return None
        return {
            "key": "avg_ns",
            "value": value,
            "unit": "ns/op",
            "better": "lower",
            "display": f"{_fmt_scalar(value)} ns/op",
        }

    throughput = _coerce_float(data.get("throughput_mb_s"))
    if throughput is not None:
        return {
            "key": "throughput_mb_s",
            "value": throughput,
            "unit": "MB/s",
            "better": "higher",
            "display": f"{_fmt_scalar(throughput)} MB/s",
        }

    return None


def normalize_benchmark_result(data: dict[str, Any]) -> dict[str, Any]:
    notes: list[str] = []
    metric = _metric_descriptor(data)

    if "avg_ns" in data:
        rate_display = f"{_fmt_scalar(data.get('avg_ns'))} ns/op, {_fmt_scalar(data.get('rate_hz'))} ops/s"
        if data.get("cycles") is not None:
            notes.append(f"cycles={_fmt_scalar(data['cycles'])}")
        if "threshold_pass" in data:
            notes.append(f"threshold_pass={_fmt_scalar(data['threshold_pass'])}")
    else:
        throughput = data.get("throughput_mb_s")
        rate_display = f"{_fmt_scalar(throughput)} MB/s" if throughput is not None else ""
        if "frames_received" in data and "frames_sent" in data:
            notes.append(f"frames={data['frames_received']}/{data['frames_sent']}")
        if "elapsed_sec" in data:
            notes.append(f"elapsed={_fmt_scalar(data['elapsed_sec'])} s")
        if "version" in data:
            notes.append(f"ver={data['version']}")
        if "jumbo" in data:
            notes.append(f"jumbo={_fmt_scalar(data['jumbo'])}")

    return {
        "name": data["name"],
        "complete": data.get("drain_complete", data.get("threshold_pass", "n/a")),
        "rx_errors": data.get("rx_errors", "n/a"),
        "rate_display": rate_display,
        "notes": notes,
        "primary_metric": metric,
        "raw": data,
    }


def build_run_summary(
    result_dir: Path,
    ref_name: str,
    sha: str,
    run_id: str | int | None = None,
    run_url: str | None = None,
    published_at: str | None = None,
) -> dict[str, Any]:
    benchmarks = [normalize_benchmark_result(data) for data in load_perf_results(result_dir)]
    benchmarks.sort(key=lambda item: item["name"])

    return {
        "schema_version": SCHEMA_VERSION,
        SAMPLE_PROVENANCE_KEY: SAMPLE_PROVENANCE_SINGLE_SAMPLE,
        "ref_name": ref_name,
        "ref_slug": slugify_ref_name(ref_name),
        "sha": sha,
        "short_sha": short_sha(sha),
        "run_id": str(run_id) if run_id is not None else "",
        "run_url": run_url or "",
        "published_at": published_at or utc_now_iso(),
        "benchmarks": benchmarks,
    }


def upgrade_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Read a published run summary of schema_version 1 or 2, or of any
    unrecognized version, and return a new in-memory dict that always carries
    the version 2 shape plus an explicit gate-eligibility marking.

    Never mutates its argument. Never adds, drops, renames, or reorders any
    pre-existing key beyond what this docstring's own additions describe, and
    never touches "benchmarks". A historical version 1 record, and any record
    this reader does not recognize, comes back marked not gate-eligible with a
    named reason, so old or unrecognized data can never silently become a gate
    baseline.

    A recognized schema_version whose sample_provenance value is absent, null, or
    outside the recognized tuple is marked not gate-eligible with
    GATE_REASON_UNRECOGNIZED_SAMPLE_PROVENANCE, distinct from
    GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION: the former means the version itself
    was recognized and only the provenance value was not, the latter means the
    version itself was not recognized.
    """
    upgraded = dict(summary)
    version = upgraded.get("schema_version")

    if version == 1:
        upgraded["schema_version"] = SCHEMA_VERSION
        upgraded[SAMPLE_PROVENANCE_KEY] = SAMPLE_PROVENANCE_SINGLE_SAMPLE
        upgraded[GATE_ELIGIBLE_KEY] = False
        upgraded[GATE_ELIGIBLE_REASON_KEY] = GATE_REASON_UPGRADED_FROM_SCHEMA_VERSION_1
        return upgraded

    if version == SCHEMA_VERSION:
        sample_provenance = upgraded.get(SAMPLE_PROVENANCE_KEY)
        if sample_provenance == SAMPLE_PROVENANCE_MULTI_SAMPLE_CLEAN:
            upgraded[GATE_ELIGIBLE_KEY] = True
            upgraded[GATE_ELIGIBLE_REASON_KEY] = None
        elif sample_provenance in SAMPLE_PROVENANCE_VALUES:
            upgraded[GATE_ELIGIBLE_KEY] = False
            upgraded[GATE_ELIGIBLE_REASON_KEY] = GATE_REASON_SINGLE_SAMPLE_PUBLISHED
        else:
            upgraded[GATE_ELIGIBLE_KEY] = False
            upgraded[GATE_ELIGIBLE_REASON_KEY] = GATE_REASON_UNRECOGNIZED_SAMPLE_PROVENANCE
        return upgraded

    upgraded[GATE_ELIGIBLE_KEY] = False
    upgraded[GATE_ELIGIBLE_REASON_KEY] = GATE_REASON_UNRECOGNIZED_SCHEMA_VERSION
    return upgraded


def benchmarks_by_name(summary: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not summary:
        return {}
    return {entry["name"]: entry for entry in summary.get("benchmarks", [])}


def summary_metadata(summary: dict[str, Any] | None) -> dict[str, str]:
    if not summary:
        return {"ref_name": "", "sha": "", "short_sha": "", "run_url": "", "published_at": ""}
    return {
        "ref_name": summary.get("ref_name", ""),
        "sha": summary.get("sha", ""),
        "short_sha": summary.get("short_sha", short_sha(summary.get("sha", ""))),
        "run_url": summary.get("run_url", ""),
        "published_at": summary.get("published_at", ""),
    }


def compare_rows(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any] | None:
    if not baseline:
        return None

    current_metric = current.get("primary_metric")
    baseline_metric = baseline.get("primary_metric")
    if not current_metric or not baseline_metric:
        return None
    if current_metric.get("key") != baseline_metric.get("key"):
        return None

    current_value = _coerce_float(current_metric.get("value"))
    baseline_value = _coerce_float(baseline_metric.get("value"))
    if current_value is None or baseline_value is None:
        return None

    delta = current_value - baseline_value
    percent = None if baseline_value == 0 else (delta / baseline_value) * 100.0
    better = current_metric.get("better")

    if delta == 0:
        verdict = "same"
    elif better == "lower":
        verdict = "improved" if delta < 0 else "regressed"
    else:
        verdict = "improved" if delta > 0 else "regressed"

    return {
        "key": current_metric.get("key"),
        "unit": current_metric.get("unit", ""),
        "delta": delta,
        "percent": percent,
        "verdict": verdict,
    }


def format_comparison(comparison: dict[str, Any] | None) -> str:
    if comparison is None:
        return "n/a"
    if comparison["verdict"] == "same":
        return "same"

    percent = comparison.get("percent")
    if percent is None:
        percent_text = "n/a"
    else:
        percent_text = f"{percent:+.1f}%"

    unit = comparison.get("unit", "")
    delta_text = f"{comparison['delta']:+.3f}"
    if unit:
        delta_text = f"{delta_text} {unit}"

    return f"{percent_text} ({delta_text}, {comparison['verdict']})"


def comparison_highlight(comparison: dict[str, Any] | None) -> str | None:
    if comparison is None:
        return None

    verdict = comparison.get("verdict")
    if verdict not in {"improved", "regressed"}:
        return None

    percent = _coerce_float(comparison.get("percent"))
    if percent is None or abs(percent) <= COMPARISON_HIGHLIGHT_THRESHOLD_PERCENT:
        return None

    return verdict


def row_highlight(comparisons: list[dict[str, Any] | None]) -> str | None:
    highlights = [comparison_highlight(comparison) for comparison in comparisons]
    if "regressed" in highlights:
        return "regressed"
    if "improved" in highlights:
        return "improved"
    return None
