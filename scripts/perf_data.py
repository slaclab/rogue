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


SCHEMA_VERSION = 1
TRACKED_BASELINE_REFS = ("main", "pre-release")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_site_root(site_root: str) -> str:
    site_root = site_root.strip()
    if not site_root or site_root == "/":
        return ""
    if not site_root.startswith("/"):
        site_root = f"/{site_root}"
    return site_root.rstrip("/")


def url_join(site_root: str, *parts: str) -> str:
    pieces = [normalize_site_root(site_root).strip("/")] if site_root else [""]
    pieces.extend(part.strip("/") for part in parts if part)
    path = "/".join(piece for piece in pieces if piece)
    return f"/{path}/" if path else "/"


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
        "ref_name": ref_name,
        "ref_slug": slugify_ref_name(ref_name),
        "sha": sha,
        "short_sha": short_sha(sha),
        "run_id": str(run_id) if run_id is not None else "",
        "run_url": run_url or "",
        "published_at": published_at or utc_now_iso(),
        "benchmarks": benchmarks,
    }


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
