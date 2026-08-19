# Retained gate-run evidence

This directory holds only the hosted gate-run artifacts that the shipped handoff documentation
in `docs/plans/perf-ci-hardening/GATE-SETUP.md` names a determination against. It follows
`coverage-proof-runs/README.md`'s shape: a scope paragraph, the retention split, one line per
retained run, the worked example, and a pointer to the sidecar that carries the parked tag.

## Retention split

The candidate evidence directories under `docs/plans/perf-ci-hardening/` were re-checked (not
copied from prior planning) across `tests/`, `scripts/`, `.github/`, and `docs/` for a real read
of each committed path, as distinct from a `tmp_path` destination created and destroyed inside a
test, or a script default that the documented step-zero already covers.

Ships (a test reads the committed path by real path):

- `probe-runs/`: `tests/utilities/test_probe_capability_report.py:646` and `:862` read
  `docs/plans/perf-ci-hardening/probe-runs` directly.
- `seeded-regressions/`: `tests/utilities/test_perf_gate_seeded_regressions.py:53` reads it
  directly.
- `gate-baseline.json` and `campaign-report.json`: read directly by
  `tests/utilities/test_perf_gate_evaluator.py:625` and
  `tests/utilities/test_perf_tier_registry.py:344` respectively.

Parked (nothing under `tests/`, `scripts/`, `.github/`, or `docs/` reads the committed path by
real path; every hit is a `tmp_path` fixture destination or a script default the documented step
zero already covers):

- `gate-validation-runs/`: `tests/utilities/test_perf_gate_validation_campaign.py` only ever
  builds `tmp_path / "gate-validation-runs"`; `scripts/perf_gate_validation_campaign.py:88`'s
  `DEFAULT_DEST` and the prose in `GATE-VALIDATION-SETUP.md`/`GATE-VALIDATION-REPORT.md` are the
  only other hits.
- `harness-runs/`: `tests/utilities/test_perf_harness_campaign.py` only ever builds
  `tmp_path / "harness-runs"`; `scripts/perf_harness_campaign.py:84`,
  `scripts/perf_campaign_report.py:64`, and `scripts/perf_gate_baseline.py:51` each default
  `DEFAULT_RUNS_DIR`/`DEFAULT_DEST` to it, covered by the documented step zero.
- `harness-runs-superseded-6b74f791/`: only doc prose and one script comment reference it; no
  test and no script default names it.
- `coverage-proof-runs/`: only doc prose (`HARNESS-SETUP.md`, its own `README.md`) references it.
- `gate-validation-hangs/`: only doc prose (`GATE-VALIDATION-SETUP.md`,
  `seeded-regressions/README.md`) references it.

This re-run confirms the expected split named in planning: nothing changed it.

## Retained runs

One line per retained hosted run: the id, the determination it backs, and which artifacts are
present in this directory.

| Run id | Determination it backs | Artifacts present |
|---|---|---|
| [`32209900074`](https://github.com/ruck314/rogue/actions/runs/32209900074) | Trusted-baseline demonstration, case 1: head commit's baseline copy neutralized to `{"cells": {}}`; evaluator still reads the trusted base-branch copy and returns PASS over 128 cells | `verdict.json`, `verdict.md`, `ab-summary.md` |
| [`32211546278`](https://github.com/ruck314/rogue/actions/runs/32211546278) | Trusted-baseline demonstration, case 2: head commit's baseline copy truncated to invalid JSON; evaluator still returns PASS over 128 cells | `verdict.json`, `verdict.md`, `ab-summary.md` |
| [`32211567707`](https://github.com/ruck314/rogue/actions/runs/32211567707) | Trusted-baseline demonstration, case 3: manual dispatch exercising the `git_merge_base_fallback` anchor path; PASS over 128 cells | `verdict.json`, `verdict.md`, `ab-summary.md` |
| [`32200785019`](https://github.com/ruck314/rogue/actions/runs/32200785019) | Escape-hatch pair, rejected half: FAIL over 128 cells with 5 failing `transaction_lock_acquisitions` cells; override `status: rejected`, `rejection_reason: justification-below-minimum-length`. Also the offline re-score worked example below | `verdict.json`, `verdict.md`, `ab-summary.md`, `ab-record.json` |
| [`32201360126`](https://github.com/ruck314/rogue/actions/runs/32201360126) | Escape-hatch pair, accepted half: same seeded regression, PASS, override `status: accepted` with the five named cells exempted | `verdict.json`, `verdict.md`, `ab-summary.md` |
| [`32189502371`](https://github.com/ruck314/rogue/actions/runs/32189502371) | The one run in the 14-run budget-accounting population whose job wall clock (683s) landed outside the 600s budget, by 83 seconds, attributed to `apt-get`-mirror latency rather than the paired-run step | `verdict.json`, `verdict.md`, `ab-summary.md` |
| [`32199459658`](https://github.com/ruck314/rogue/actions/runs/32199459658) | The one evidence-bar run whose retry actually fired: `run.attempts` carries two entries, first attempt `retried: true`, both INCONCLUSIVE | `verdict.json`, `verdict.md`, `ab-summary.md` |
| [`32199495589`](https://github.com/ruck314/rogue/actions/runs/32199495589) | The one evidence-bar run recorded with `run.cold_cache: true` (candidate leg's ccache hit rate was zero), still PASS and still inside the 600s budget | `verdict.json`, `verdict.md`, `ab-summary.md` |
| [`32159830013`](https://github.com/ruck314/rogue/actions/runs/32159830013) | The frame-batching diagnosis run: first clean `merge_base`-leg `combiner_count` baseline for the `disable-frame-batching` seeded regression across eleven total dispatches; candidate leg produced zero completed rounds; verdict INCONCLUSIVE, reason `metric-absent-from-leg`. Backs the accepted written determination that this seeded regression's detectability stays an open question rather than a closed gate failure | `verdict.json` only; this run's artifact never carried a `verdict.md` or `ab-summary.md` in the committed population it was retrieved from |
| `32070224879` | Pre-`CCACHE_BASEDIR`-fix cold-cache worst case: a freshly frozen branch's first-ever dispatch, 758s job wall clock, exceeded the 600s budget by 158s | `verdict.json`, `verdict.md`, `ab-summary.md` |
| `32073814745` | Post-fix cold-cache worst case: the same scenario after the ccache fix, 624s job wall clock, exceeded the 600s budget by 24s | `verdict.json`, `verdict.md`, `ab-summary.md` |

## Offline re-score worked example

`32200785019-ab-record.json` is the one full paired-run record retained in this directory, per
the plan that produced it. It is a real pull-request gate run carrying a FAIL verdict over 128
gating cells with five failing `transaction_lock_acquisitions` cells, and its override block
carries `status: rejected`, `rejection_reason: justification-below-minimum-length`, making it
simultaneously the worked example for reading a FAIL summary, the worked example for the
reproduction command below, and the exhibit for the rejected-override rendering gap named in
`GATE-SETUP.md`'s inherited-gaps section.

Reproduce:

```
python3 scripts/perf_gate_evaluator.py \
  --record docs/plans/perf-ci-hardening/gate-runs/32200785019-ab-record.json \
  --baseline docs/plans/perf-ci-hardening/gate-baseline.json \
  --out-json <path> --out-md <path>
```

This exits 0 and the rendered markdown reports `Gating cells evaluated: 128`, matching the
original run's own verdict.

## What is not in this directory

The full 150 MB evidence population, every paired-run record in `gate-validation-runs/`, both
harness populations, the coverage-proof runs, and the hang diagnostics, is not shipped here.
Those directories stay in the working tree for now; the mechanism that excludes them from the
pull request itself is a later plan's fresh-branch step, not this directory. What this directory
guarantees is narrower and already true: every hosted run id a shipped determination rests on has
an artifact a reader can open, right here, rather than only a cited id with nothing behind it.

The full populations are made reachable after that later cut by a published annotated tag on the
`ruck314/rogue` fork. Its name, resolved commit, and the directories reachable only through it are
recorded once, as data, in `evidence-tag.json` in this directory: quote that file rather than
this prose for the tag name or commit.
