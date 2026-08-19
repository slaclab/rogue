# Perf CI Hardening: Completion Record

This record replaces the working narratives that documented this effort phase by phase. Each of
those narratives froze its own numbers at the population size that existed on the day it was
written, and three of them quote three different figures for the same paired-mechanism cost as a
direct result. This record exists to carry forward only what a maintainer needs and can check: what
landed, the durable procedures, and the measured costs recomputed once, over the population as it
stands today, with the artifact that backs each figure named beside it. What changed, why the
paired same-job comparison was chosen over the alternatives considered, what validation was run
against it, what still does not close, and where the permanent artifacts live: this file answers
each in turn.

## What shipped

- A tiered measurement harness and a declarative metric registry (`tests/perf/_perf_harness.py`,
  `scripts/perf_tier_registry.py`): 55 registered metrics, of which 22 are bound to the top,
  deterministic tier that the gate is allowed to block on.
- Counter instrumentation on the transaction path and the stream path (`include/rogue/PerfCounters.h`,
  `src/rogue/PerfCounters.cpp`, plus the call sites those counters attach to across the transaction,
  GIL-crossing, and stream I/O code paths).
- A paired same-job comparison against the pull request's own merge base, through two `git worktree`
  checkouts sharing one job's object store and one shared compiler cache (`scripts/perf_gate_ab_runner.py`).
- A standalone evaluator that returns exactly one of three verdicts, PASS, FAIL, or INCONCLUSIVE, for
  any two-leg measurement record (`scripts/perf_gate_evaluator.py`).
- The pull-request-triggered gate workflow itself, with its one narrow, scope-limited retry and its
  commit-trailer escape hatch (`.github/workflows/perf_gate.yml`).
- The baseline generator and its committed sidecar pair, which together decide which cells are
  eligible to gate at all (`scripts/perf_gate_baseline.py`, `docs/plans/perf-ci-hardening/gate-baseline.json`,
  `docs/plans/perf-ci-hardening/GATE-BASELINE.md`).
- The contributor-facing documentation a red check actually points a reader at (`tests/perf/README.md`).
- Retained hosted-run evidence for every determination this record cites by run id, under
  `docs/plans/perf-ci-hardening/gate-runs/`, with the published fork tag recorded once in that
  directory's `evidence-tag.json` sidecar for everything too large to carry in the repository.

Every count below is read from the committed baseline sidecar's own census, not typed by hand: 525
total (benchmark, metric) cells, of which 128 gate under an exact-equality rule, spanning 22 gating
metrics across 16 benchmarks.

## The baseline is not a threshold table

This is the single most load-bearing conceptual correction in the whole handoff, and a reader who
misses it will misread everything downstream. With same-job paired measurement, every gating
decision compares the candidate leg's own measured value against the merge-base leg's own measured
value, both built and measured inside the same job, on the same runner, in the same dispatch. The
committed baseline sidecar never enters that comparison at evaluation time: the evaluator's
exact-equality gating rule compares the two legs' own values to each other, never to the baseline's
own recorded observed value. The baseline decides two things and only two things: which cells gate
at all, and, implicitly by the same sidecar entry, which tier and which recorded dispersion justify
gating each one.

The consequence follows directly. A change that legitimately moves a counter does not require the
baseline to be regenerated, because the next pull request's own merge base already carries the
change once this one merges. The recorded dispersion in the baseline is not a live comparand either:
it is used to decide which cells are eligible to gate in the first place, and to raise an
informational drift note when a passing value falls outside its recorded minimum-to-maximum band.

What updating a threshold actually means splits into two cases that require different action. A
one-time intentional change, where a specific pull request's own regression is real and accepted, is
handled entirely by the commit-trailer escape hatch described below: the named cells are exempted
for that one pull request's own verdict, the baseline is never touched, and no other pull request is
affected. A change to the gating cell set itself, where the population of what should gate has
genuinely shifted, is handled by regenerating the baseline from a committed measurement population
using the generator's own printed canonical command, landing in its own commit that cites the report
justifying the regeneration, followed by re-running the validation report generator over the
unchanged committed population to confirm its output reproduces byte for byte. Hand-editing the
sidecar directly is not a substitute for either path: a hand-edited number carries no derivation, no
observed sample count, and no CPU-model evidence, and decouples the committed baseline from the
measurement population it claims to summarize.

## Baseline trust model

The prior section states what the baseline decides. This one states where that decision actually
comes from, why that source is trusted, and what is deliberately left outside that trust rather than
quietly assumed away.

Both the paired-run step and the evaluate step read the gate baseline from a dedicated extraction
step's own copy, never from the pull request's own checked-out worktree. That extraction step
resolves the merge-base commit's own object by git plumbing, at the sha the merge-base resolution
step itself already validated: on a pull request this is the base branch's own tip at event time; on
a manual dispatch, which carries no pull-request payload, it is a real `git merge-base` computation
against the fetched base ref. The extracted copy is written entirely outside the pull request's own
checkout, and it is the only baseline either the in-job retry decision or the final verdict ever
receives.

Why that ref is trusted: a commit reaches the base branch's own tip only through this project's
review process, and a contributor opening a pull request cannot place a commit there without write
access to the repository, a different and stronger permission than the ability to open a pull
request. That buys exactly one thing: the baseline a gate run reads cannot be chosen by the same
change the gate is judging. It does not buy correctness of the baseline's own numbers.

The residual risk is named rather than hidden: a baseline change that reaches the base branch through
ordinary review is trusted by construction. Nothing in the shipped design re-derives or re-checks the
baseline's own numbers against anything else beyond that review. The one mitigating signal that
exists is an informational comparison against the pull request's own tree copy of the baseline file,
surfaced in the step summary so a reviewer who reads it sees a baseline edit without having to diff
for it; nothing enforces that a reviewer actually reads it.

Three distinguishable outcomes must not be conflated. A trusted baseline that is absent, unreadable,
unparseable, or missing its cell mapping is an infrastructure failure: it produces no verdict
artifact at all, and the evaluator exits non-zero, before any measurement cost is paid. A baseline
that parses correctly but declares no gate-eligible cell resolves to a non-blocking INCONCLUSIVE
verdict carrying the zero-gating-cell reason, exactly as a baseline that happens to carry only
non-gating cells already would. An INCONCLUSIVE measurement outcome against a valid, populated
baseline, for any of the ten enumerated measurement-uncertainty reasons, is a third and distinct
thing again: a real measurement's own uncertainty, unrelated to whether the baseline itself could be
read. None of the three is the same as another, and an INCONCLUSIVE outcome never blocks a pull
request in either of the latter two cases; an infrastructure failure is not a verdict at all.

The pull request's own tree copy of the baseline is still compared, but only as an informational
audit signal: a content-hash comparison against the trusted copy, reported in the step summary as
whether the pull request's own copy differs from the one the gate actually used to decide the
verdict.

## Escape hatch

A single commit-trailer key, `Perf-Gate-Override`, read from the pull request's head commit only:
a trailer on an earlier commit of the same branch has no effect, and pushing a new commit re-reads
the trailer from the new head. The grammar is a comma-separated list of `benchmark.metric` cell
tokens, then a semicolon, then a justification. The justification's minimum length is 20 Unicode
code points, counted on the whitespace-stripped value: a value of exactly 20 code points is
accepted, and one fewer is rejected.

A named cell exempts only itself for that one pull request's own verdict, not the whole run. A
rejected attempt exempts nothing at all, and is now disclosed in the step summary with its status,
its reason, its author, and the trailer as written, rather than leaving a reader to guess whether an
override was even attempted. A trailer is rejected for exactly one of five reasons:

- `no-semicolon-separator`: the value carries no semicolon at all.
- `empty-justification`: the text after the semicolon is empty once stripped.
- `justification-below-minimum-length`: the justification is under 20 code points.
- `empty-cell-list`: the text before the semicolon named no cell at all.
- `malformed-cell-token`: a named cell does not match the `benchmark.metric` pattern.

A named cell that is not failing, is not gating, or is absent from the baseline is not silently
ignored either; each of those three conditions is recorded with its own distinct reason
(`gating-but-not-failing`, `present-but-not-gating`, `absent-from-baseline`) rather than folded into
a generic unmatched bucket.

The retained evidence for this mechanism is a real rejected-and-accepted pair against the same
seeded regression, both under `docs/plans/perf-ci-hardening/gate-runs/`: run `32200785019` (FAIL
over 128 cells, override rejected with `justification-below-minimum-length`, also the offline
re-score worked example below) and run `32201360126` (the same regression, override accepted with
the five affected cells named, verdict PASS). The contributor-facing procedure for writing a
trailer, including the case where the change is an intentional improvement rather than a
regression, lives in `tests/perf/README.md`; this section states the live grammar and its real
evidence, not the procedure a contributor follows, so the two do not drift into two different
descriptions of the same mechanism.

## Measured cost of the paired mechanism

Recomputed directly from `timings.total` in every committed two-leg record under
`docs/plans/perf-ci-hardening/gate-validation-runs/` as that population stands today: 73 files,
median **350.77 seconds**, against the single declared 600 second budget that
`scripts/perf_gate_evaluator.py` holds as its one declaration (`scripts/perf_gate_validation_report.py`
mirrors it rather than declaring the figure a second time). That leaves **249.23 seconds** of
headroom at the population median.

Three figures for this same measurement have been quoted before this one, each frozen at the
population size that existed when it was written, and each is superseded here rather than left to
contradict this one silently: 345.52 seconds, over a 69-record population measured earlier in this
campaign; 349.12 seconds, quoted in a later reconciliation pass over a population that had grown
past 69 but had not yet reached 73; and now 350.77 seconds, over the full 73-record population as
committed today. The 73-record figure is the one to use; the other two describe populations that no
longer reflect what is committed.

The measured cost per round per leg is **85.08 seconds for the candidate leg** and **84.47 seconds
for the merge-base leg**. `scripts/perf_gate_ab_runner.py` enforces a floor of 180 seconds (twice the
candidate-leg figure, rounded up to the next whole minute) on each round's own share of the
remaining time budget for one leg, so a round is skipped outright, with its own recorded reason,
rather than started with a share too small to use. Exactly one retained run had its retry actually
fire: `32199459658`, whose own committed record reports a `retried_total_seconds` of approximately
**40.16 seconds** for the added retry pass, folded into that run's own `total_seconds` of 363.16
seconds rather than hidden elsewhere.

## Reproducing a collected run offline

The full contributor-facing procedure, including the working local invocation that does collect
today, lives in `tests/perf/README.md`; this section states only what belongs beside the measured
cost above rather than duplicating that procedure. The evaluator itself imports nothing but the
Python standard library, so re-scoring a committed two-leg record against the committed baseline
needs no build and no environment activation.

Every canonical reproduce command a generated report prints for itself is byte-identical to the
command that produced that report. Two of those commands default to a measurement population that
is not carried in this repository. The step-zero remedy for either is to fetch the published
annotated tag recorded in `docs/plans/perf-ci-hardening/gate-runs/evidence-tag.json`, then run the
unchanged command from that checkout; the sidecar carries the tag's name and resolved commit, so
neither is repeated here. Nothing was regenerated to avoid this gap: the byte-stability checks over
these generated artifacts have twice caught real generator defects in this project, and a
regeneration undertaken only for cosmetic reasons would put that safety net at risk for no gain.

## Budget accounting

The single declared budget the evaluator holds is 600 seconds. The determination against it is
**partially met**, not met: a recorded run has exceeded it, and this section names every one of
them with its measured figure and its attributed cause, then names the one condition still missing
before that determination could close.

The gate has been dispatched against real pull requests fourteen times to date. Of the eleven runs
that were not individually retained, the whole-job figures are carried forward as a historical
measurement rather than independently reproduced here, since no separately committed per-run
artifact survives for them: median **432.5 seconds**, minimum **413 seconds**, maximum **683
seconds**, thirteen of the fourteen inside the 600 second budget. Three of the fourteen are retained
as openable artifacts under `docs/plans/perf-ci-hardening/gate-runs/`, and their figures below are
read directly from those committed files, both the whole-job figure and that same run's own
paired-run step total side by side, so the choice of denominator hides nothing:

| Run id | Job wall clock (s) | Paired-run step total (s) | Against the 600s budget |
|---|---|---|---|
| `32189502371` | 683 | 353.73 | outside, by 83 seconds (job); the paired-run step itself finished comfortably inside budget |
| `32199459658` | 463 | 363.16 | inside; the one run whose retry actually fired, adding about 40.16 seconds |
| `32199495589` | 582 | 510.53 | inside; the one run recorded with a cold candidate-leg cache |

The one run that exceeded the whole-job budget, `32189502371`, is attributed to dependency-mirror
latency on the install step rather than to the paired measurement itself: that same run's own
paired-run step total, 353.73 seconds, is comfortably inside budget on its own, so the overage was
not the measurement. Read against the fourteen-run population's own whole-job median of 432.5
seconds, the headroom to 600 seconds does not buy even one additional measurement round per leg at
the measured per-round-per-leg cost above; read against the paired-run step's own timer instead, it
buys one.

The trusted-baseline demonstration adds three more measured wall clocks, from three real hosted
runs proving the baseline-extraction fix: **686 seconds** (outside the budget, by 86 seconds), **594
seconds** (inside, by 6 seconds), and **449 seconds** (inside, by 151 seconds). Three runs are not a
population and do not close this determination on their own; they are reported because a
determination-bearing run is reported regardless of which mechanism it was dispatched to prove.

Two earlier cold-cache single samples are carried forward rather than re-measured: a first-ever
dispatch against a freshly frozen branch at **758 seconds** (exceeded by 158 seconds), and the same
scenario after a build-cache misconfiguration was fixed, at **624 seconds** (exceeded by 24 seconds).
A pull request from a genuinely separate fork runs cold-cache by construction on its first dispatch,
which is why these two single samples matter more than their count of two suggests: they are the
closest measured proxy this project has for that scenario, not two data points to be dismissed for
being few.

Separately, in the larger 73-record paired-measurement population the prior section's median is
computed over, five of the 73 committed records carry a `timings.total` above 600 seconds rather
than the fourteen-run gate population's own single overage. One is the pre-cache-fix cold-cache run
already named above (`timings.total` 682.07 seconds, whole-job 758 seconds). The other four are
read directly from their own committed record rather than inferred from run-id adjacency:
`32159830013` (765.13 seconds) and the three records `32104913039`, `32106870977`, and
`32108819426` (1200.56, 1201.15, and 1203.85 seconds) each carry `label: seeded-search` and
`patch_name: disable-frame-batching.patch` in their own committed record, with `measure_candidate`
reporting zero completed candidate measurement rounds in every one of the four despite each leg's
own build subprocess exiting normally. These four are the same seeded-regression diagnosis attempt
this project's decisions record already carries as an accepted, unproven override: a real hang
inside the patched benchmark's own process, not a defect in the paired mechanism itself, and not
four independent unexplained outliers.

The missing condition that would close this determination, stated in one sentence: a recorded
population of real gate dispatches with zero overages, which this project does not have.

The other half of the same determination is the deep and long-running measurement workflows. Their
trigger blocks, parsed directly rather than transcribed by eye, are `{push: {branches:
["perf-harness/**"]}, workflow_dispatch: {...}}` and `{push: {branches: ["perf-gate/**"]},
workflow_dispatch: {...}}`: neither declares a `pull_request` trigger anywhere in its `on:` block,
so neither can ever run on a pull-request event or block one. This absence is machine-checkable
against the two workflow files themselves, not merely read by eye, and it is the whole discharge of
the requirement that a deep or long-running measurement can never block a pull request.

## Where the evidence lives

What ships in the repository: every generated report and its versioned sidecar; the probe
population and the seeded-regression patches, because live tests read them by path; the committed
baseline and campaign sidecars, for the same reason; the retained per-run verdict artifacts under
`docs/plans/perf-ci-hardening/gate-runs/`; and exactly one full paired-run record, kept there as the
offline re-score worked example this record and `tests/perf/README.md` both point at.

What does not ship: the full paired-run population and the two harness populations. Nothing under
`tests/`, `scripts/`, or the workflows reads either by its committed path, and both are large enough
that a pull request carrying them could not be read line by line. This deliberately relaxes this
project's own convention of committing every raw record beside the generated aggregate it feeds,
and says so here rather than letting a reader discover it by absence. Both are reachable instead
through a published annotated tag on the `ruck314/rogue` fork, whose name, resolved commit, and the
directories reachable only through it are recorded once, as data, in
`docs/plans/perf-ci-hardening/gate-runs/evidence-tag.json`; this record quotes that sidecar rather
than restating either value.

What is lost if the fork holding that tag disappears: the ability to regenerate any of the shipped
reports from their raw inputs, and the ability to recheck the paired-mechanism cost figures against
the population they were computed from. What stays checkable from the shipping tree alone: every
figure backed by a retained per-run artifact under `gate-runs/` (the evidence-bar runs, the
trusted-baseline demonstration runs, the escape-hatch pair, and the named budget-accounting
outliers), the offline re-score worked example, and the generated baseline and campaign artifacts
that do ship. The paired-mechanism cost figures in `## Measured cost of the paired mechanism`
above, the 350.77 second median chief among them, are the one figure class that does not clear
that bar: they were recomputed directly over the 73-record population under
`gate-validation-runs/`, and that directory is one of the two large populations this record
deliberately does not ship, reachable only through the tag recorded in `evidence-tag.json`. A
reader who wants to recheck that median, rather than take this record's word for it, needs the
tag, not just this pull request.

## Evidence bar for the blocking flip

Before the gate was flipped from report-only to blocking, a bar was set and then measured rather
than assumed: ten real pull-request gate runs, each changing only a single line of this
repository's own unrelated documentation prose, so any gating failure on any of them would be a
false positive by construction. The branch carrying them was pushed one commit at a time so each
commit produced its own run, and all ten ran to completion independently with no cancellation.

All ten runs completed with a successful job conclusion, and every one of the ten reported zero
failing gating cells. The evidence bar's central claim, zero spurious gating failures on unchanged
code, is met by direct count rather than by sampling: 0 of 10.

The same measurement also produced an inconclusive rate, reported honestly against what was
expected going in rather than only against itself. The rate expected before any real pull-request
run existed was about one inconclusive outcome in fifteen runs (roughly 6.7 percent), derived from
an earlier null-hypothesis population. The rate measured across these ten real runs was one in ten
(10.0 percent) on the first attempt, and one in ten (10.0 percent) after the single automatic
retry, because that run's own retry reproduced the same measurement-uncertainty condition rather
than resolving it. The measured figure supersedes the prior expectation as the number that should
guide a reader going forward; both are stated here side by side rather than folded into one, since
the measured population is the more relevant of the two.

| Run id | Verdict | Gating cells | Failing cells | Retry ran | Wall clock (s) |
|---|---|---|---|---|---|
| [`32199397623`](https://github.com/ruck314/rogue/actions/runs/32199397623) | PASS | 128 | 0 | no | 413 |
| [`32199437583`](https://github.com/ruck314/rogue/actions/runs/32199437583) | PASS | 128 | 0 | no | 428 |
| [`32199446386`](https://github.com/ruck314/rogue/actions/runs/32199446386) | PASS | 128 | 0 | no | 423 |
| [`32199454039`](https://github.com/ruck314/rogue/actions/runs/32199454039) | PASS | 128 | 0 | no | 415 |
| [`32199459658`](https://github.com/ruck314/rogue/actions/runs/32199459658) | INCONCLUSIVE | 128 | 0 | yes | 463 |
| [`32199465555`](https://github.com/ruck314/rogue/actions/runs/32199465555) | PASS | 128 | 0 | no | 418 |
| [`32199473616`](https://github.com/ruck314/rogue/actions/runs/32199473616) | PASS | 128 | 0 | no | 473 |
| [`32199480123`](https://github.com/ruck314/rogue/actions/runs/32199480123) | PASS | 128 | 0 | no | 440 |
| [`32199485540`](https://github.com/ruck314/rogue/actions/runs/32199485540) | PASS | 128 | 0 | no | 432 |
| [`32199495589`](https://github.com/ruck314/rogue/actions/runs/32199495589) | PASS | 128 | 0 | no | 582 |

Run [`32199459658`](https://github.com/ruck314/rogue/actions/runs/32199459658) is the one run in
this population whose retry actually fired: its own record carries two attempts, both
inconclusive for the same reason, and a retained artifact for it lives under
`docs/plans/perf-ci-hardening/gate-runs/`. Run
[`32199495589`](https://github.com/ruck314/rogue/actions/runs/32199495589) is the one run in this
population recorded with a zero percent cache hit rate on its own candidate leg, the slowest of
the ten at 582 seconds and still comfortably inside the 600 second budget; its retained artifact
lives in the same directory. The other eight runs passed on their first attempt with no retry and
carry no individually retained artifact, since nothing about any one of them needed one beyond the
aggregate zero-failing-cells count already stated above.

## Trusted baseline demonstration

Three real hosted runs prove the trusted-baseline fix on the exact commit this record ships, not
on an intermediate state, and back the trust-model claim stated in `## Baseline trust model`
above: both the paired-run step and the evaluate step read the gate baseline from a dedicated
extraction step's own copy, anchored at the base branch's own commit, and never from the pull
request's own checked-out tree.

The first run, [`32209900074`](https://github.com/ruck314/rogue/actions/runs/32209900074), opened
a pull request whose head commit replaced its own copy of the committed baseline with a valid,
empty cell map. Before this fix, both consumers read that same file straight out of the pull
request's own checkout, so this exact commit would have handed the evaluator a zero-cell baseline
and produced a non-blocking inconclusive verdict for the wrong reason: not because nothing
regressed, but because nothing was left to check. The real run instead evaluated against the base
branch's own 128-cell baseline and returned PASS.

The second run, [`32211546278`](https://github.com/ruck314/rogue/actions/runs/32211546278),
amended the same pull request one step further, truncating its own baseline copy to text that
does not parse as JSON at all. Before this fix, that would also have resolved to the pull
request's own unreadable copy, which at the time was the only baseline either consumer had, and
would have silently substituted a zero-cell baseline rather than failing loudly. The real run
again evaluated against the base branch's own 128-cell baseline and returned PASS, never opening
the pull request's own corrupted copy at all.

The third run, [`32211567707`](https://github.com/ruck314/rogue/actions/runs/32211567707), was a
manual dispatch against the same throwaway branch, carrying no pull-request payload at all and so
exercising the fallback path that computes the anchor commit by a real merge-base computation
against the fetched base ref rather than reading it out of a pull-request event's own fields. It
resolved to the identical base-branch commit as the other two runs, read the identical trusted
baseline, and returned the identical PASS over 128 cells: the fallback path's first real
observation, not an inference from its own branching logic.

Recorded honestly rather than omitted: two of these three runs' first attempts failed before
producing any measurement at all, on a dependency-mirror timeout fetching an unrelated build
package; both were redispatched as a fresh attempt of the same run, and the figures below report
the successful attempt. This was an infrastructure failure, not a defect in the fix: the
trusted-baseline extraction step itself had already run and succeeded before the dependency
install step failed.

| Run id | What it proved | Trusted gating cells | Verdict | Extraction step (s) | Job wall clock (s) |
|---|---|---|---|---|---|
| [`32209900074`](https://github.com/ruck314/rogue/actions/runs/32209900074) | head commit's own baseline copy neutralized to an empty cell map; evaluator still read the base branch's own copy | 128 | PASS | under 1 | 686 |
| [`32211546278`](https://github.com/ruck314/rogue/actions/runs/32211546278) | head commit's own baseline copy truncated to invalid JSON; evaluator still read the base branch's own copy | 128 | PASS | under 1 | 594 |
| [`32211567707`](https://github.com/ruck314/rogue/actions/runs/32211567707) | manual dispatch, no pull-request payload, exercising the merge-base fallback anchor path | 128 | PASS | under 1 | 449 |

Every retained artifact for these three runs lives under `docs/plans/perf-ci-hardening/gate-runs/`.
The trusted extraction step measured under one second on every run, because the merge-base commit
and its baseline object were already present in the local object database by the time the step
ran; the paired-run step itself, measured separately, took 377, 493, and 355 seconds respectively
on the three runs, comfortably inside its own deadline. All three runs together are the proof that
a pull request cannot choose or corrupt the baseline it is judged against: the pull request's own
tree copy was neutralized, then corrupted, and the verdict never moved.

## Branch protection procedure

The gate exits non-zero on a failing verdict once blocking mode is active, but nothing on this
repository's own side enforces that outcome until a maintainer marks the check required on the
base branch. Until that one setting is applied, the gate is advisory in practice: nothing stops a
pull request from being merged past a failing verdict.

The exact check name a maintainer must select, transcribed directly from the workflow file rather
than guessed at, is **`Perf Gate`**, the job's own frozen `name:` value, never the workflow's own
display name and never the job's short id. Branch protection matches a required check by this
exact name; a later rename of the job's own name would silently break protection with nothing
surfacing the break anywhere.

The mechanism actually observed on the real target repository during this work, queried live
rather than assumed, is classic branch protection: the base branch already carries one classic
rule with required checks configured, and no repository ruleset exists anywhere on that
repository. Because classic protection permits exactly one rule per branch, the procedure below
appends `Perf Gate` to the existing rule in place; it does not create a second, competing rule and
does not touch the checks already required there.

**Action required, and the one action no commit in this record can perform:**

- [ ] On the base branch's existing branch-protection rule, under "Require status checks to pass
      before merging," add `Perf Gate` alongside the checks already required there. Leave every
      existing required check untouched; this addition is purely additive.
- [ ] Before searching for it in the required-check picker, confirm the gate job has completed
      successfully at least once against the real target repository itself, not only against a
      demonstration fork: the picker only lists a check that has actually run to a successful
      conclusion against the specific repository being configured.
- [ ] Once the setting is saved, record the date applied and who applied it in whatever change
      record this repository normally keeps for administrative settings changes.

This is a repository-settings action, not a commit: nothing in this record's own git history
performs it, and nothing in this codebase can perform it on a maintainer's behalf.

Two workflows carry every long, deep measurement campaign this project actually runs: one drives
the tiered measurement harness's own campaign, the other drives the paired same-job comparison
mechanism's own validation campaign, both already exercised across hundreds of hosted dispatches.
Neither declares a `pull_request` trigger anywhere in its own trigger configuration; each starts
only on a push to its own dedicated branch pattern, or on an explicit manual dispatch. This is
checkable directly against the two workflow files themselves, not merely read by eye:

```sh
python3 -c "import yaml; ts=[sorted(yaml.safe_load(open(p)).get('on', yaml.safe_load(open(p)).get(True))) for p in ('.github/workflows/perf_harness.yml','.github/workflows/perf_gate_validation.yml')]; assert all('pull_request' not in t for t in ts), ts; print(ts)"
```

This prints `[['push', 'workflow_dispatch'], ['push', 'workflow_dispatch']]` and exits zero.
Because neither workflow can ever be triggered by a pull-request event, a long campaign dispatched
against either one, however long it runs and however it concludes, can never appear on a pull
request's own checks list and can never block one. This absence is the whole discharge of the
requirement that a deep or long-running measurement can never block a pull request.

## Inherited open gaps

Eleven items carry forward from earlier work and from this record's own accumulated findings, each
stated with what is open, what evidence exists, and the specific condition still missing to close
it. None is presented as closed here; the one item this phase does close is recorded separately,
immediately after this list.

1. **The disabled-frame-batching regression's second, still-unidentified lock.** Never detected on
   any population across eleven hosted dispatches spanning four frozen branches. Closed for now by
   an explicit, attributed override carrying no measured magnitude, not by a detection. The most
   recent dispatch obtained the first clean control measurement on the unaffected leg and localized
   the hang to the patched benchmark's own code path rather than to benchmark ordering or
   shared-runner strain, and two of a three-dispatch retest budget were preserved unspent by
   judgment rather than exhausted. Missing: a fix for the patch's own second lock, and, once a fix
   exists, a hosted dispatch that produces a clean sample so the regression's magnitude can finally
   be measured.
2. **The small artificial per-transaction delay is a designed blind spot, not an accidental gap.**
   The deterministic tier the gate blocks on deliberately never gates on wall-clock or
   processor-time metrics, so this seeded regression changes only timing, never a deterministic
   count, and is therefore invisible to the gate by design, exactly as the tier philosophy intends.
   Missing, and ruled out on purpose rather than left unaddressed: a gating rule written over a
   timing metric, which no future phase should add without deliberately revisiting this decision
   first.
3. **A calibration-normalized second-tier gating comparison has never been exercised on any
   population.** Every gating cell shipped today is a first-tier, deterministic, exact-equality
   cell; no population measured across this project's history, including this record's own
   validation work, has run a real calibration-normalized comparison through the gate. Missing: a
   future validation campaign that runs such a comparison and reports whether normalizing against a
   calibration kernel actually flattens the metric against runner CPU model on real
   gating-relevant data, not only on the calibration kernel itself.
4. **The normalized processor-time-per-unit-work metric remains uncovered by any benchmark.** No
   shipped benchmark module measures a normalized CPU-time-per-byte or CPU-time-per-transaction
   quantity end to end. Missing: a benchmark that actually exercises this metric family, followed by
   the same cross-CPU-model reproducibility proof every other deterministic-tier metric already
   carries.
5. **Gate behavior under a real, nonzero cloud-provider processor steal delta is untested, and not
   closable on the runner fleet actually observed.** Every measurement window recorded across every
   campaign this project has run, including this record's own validation and gate runs, has shown a
   zero steal delta. This is not evidence the gate handles steal correctly; it is an inherited
   absence of the condition needed to test it. Missing: a real, nonzero steal delta observed in any
   future measurement window on this same hosted fleet; until one appears, this gap cannot be
   closed by more measurement alone.
6. **Three probe defects from the runner capability work remain open, and only a fresh probe closes
   them.** A zero-counted measurement instrument was graded usable rather than demoted, and was
   then confirmed usable-with-zero-counts across a full probe population rather than corrected;
   separately, the probe workflow has never exercised more than one repeat per measurement, so the
   repeatability admission gate meant to grade an instrument's consistency across repeats has never
   actually been evaluated by a real campaign. Missing: a future re-probe campaign that either
   changes the graded verdict on real evidence or confirms it by actually running more than one
   repeat.
7. **The trailer-parser-unavailable fail-closed path has never fired on a real hosted run.** Every
   run this project has dispatched found the trailer-parsing subcommand present; the path that
   fails closed when it is missing is proven only by unit coverage. Missing: a hosted runner image
   old enough to lack that subcommand, or a run deliberately dispatched against one, observed
   actually firing that path in practice.
8. **The trusted-branch residual risk is named, not hidden, and stays open.** A baseline change
   that reaches the base branch through this project's own ordinary code review is trusted by
   construction once it lands; nothing in the shipped design re-derives or re-checks that baseline's
   own numbers beyond the review itself, and the one disclosure signal that exists, an informational
   comparison flagging a pull request's own edited copy, does not force a reviewer to read it.
   Missing: an enforcement mechanism rather than only a disclosure signal, which would need a review
   rule scoped specifically to the committed baseline file, a repository-settings change of the same
   shape as the branch-protection action above.
9. **Branch protection on the real target repository has not been applied.** It is a
   repository-settings action, not a commit, and nothing in this record could perform it. The
   procedure and the exact required check name are recorded above; the applied-date record stays
   blank until a maintainer with admin access on that repository follows it.
10. **A closing reconciliation must read its own phase's review, not only its own plans, and that is
    a practice this record follows rather than a one-time fix.** A finding raised by a code review
    reaching this project shortly before an earlier closing account was first written did not make
    it into that account at the time; the fix already existed, but the finding about the shipped
    design's own trust model simply was not carried forward into the closing narrative until a later
    pass corrected it. The practice this argues for, and that this record now follows throughout:
    read the review of the work being closed, and either carry every finding forward or state
    plainly why not, one line per finding, rather than writing a closing account from the delivered
    changes alone.
11. **Planning-system references survive in generator output and in one workflow file, and one
    further reference predates this work entirely.** Eighteen references to this project's own
    private planning identifiers survive inside two files a report generator produces (twelve in
    the rendered markdown report, six in its JSON sidecar), because removing them would mean editing
    the exact strings the generator emits and regenerating both files, and regenerating either was
    deliberately excluded from this work: the byte-stability check tying those exact bytes to the
    already-committed files has twice caught a real generator defect in this project's history, and
    a regeneration undertaken only to erase a citation would put that safety net at risk for no
    gain. Reaching one level earlier, twelve of those same references also live inside the
    generator's own source, in the exact string literals that produce them when the generator runs,
    for the identical reason; one further reference lives inside a workflow file's own step-output
    text rather than a comment, left untouched because this project's own rule for that pre-existing
    file forbids changing that kind of text. A separate, single reference in one interface test
    module predates this work entirely and was deliberately left untouched on purpose, since
    touching it would be an edit to code this work has no business changing. Missing: a
    generator-and-regeneration change that is out of this record's own scope, taken up deliberately
    rather than as a byproduct of a citation sweep.

### Items this phase closes

**A rejected escape-hatch attempt used to render nothing at all in the step summary.** Confirmed on
a real hosted run: a contributor whose written justification was too short saw the failing cells
and no indication that an override had even been attempted, because the renderer only emitted its
escape-hatch section when an override was accepted, never when one was rejected. This is now
closed in code and under test: `render_summary_markdown` renders a rejected override's own status,
its rejection reason, its author, and the trailer text as written, in a body kept structurally
separate from the accepted-override body, with dedicated render-coverage tests pinning the
rejected case, the one-line-and-bounded rendering of the raw trailer text, and the unchanged
accepted-case body. Stated plainly rather than implied: this fix has been exercised by unit tests,
not yet by a real hosted run since it landed. The real hosted run that exists for this item is the
one that showed the omission before the fix, not one that has since exercised the fix itself.

**An accepted override's own justification, and a rejected override's own raw trailer text, could
carry contributor-supplied content into the step summary with weaker bounding than the rest of that
section applied.** A review of this same escape-hatch rendering work found that the accepted path
rendered its justification with no line-collapsing and no length ceiling at all, unlike the
sibling rejected path a few lines below it, so a written justification could inject its own
markdown heading, table, or unbounded block of text straight into the summary. A related gap sat in
the rejected path's own existing bounding: an embedded backtick in the raw trailer text was never
neutralized before the caller wrapped it in a single pair of backticks, closing that code span
early and letting the remainder render as ordinary markdown instead of staying inert. Both paths
now collapse interior newlines onto one line, neutralize embedded backticks, and truncate at a
fixed character bound before rendering, so the accepted and rejected paths share the same bounding
rather than one being weaker than the other. This is closed in code and under test, with coverage
proven to fail against the unfixed renderer and pass against the fixed one; it has not yet been
observed on a real hosted run.

**A trusted baseline that does not exist yet at the merge base produced a hard failure with no
verdict at all, rather than the non-blocking inconclusive the documentation already promised.**
Confirmed on the gate's first real dispatch against a genuine pull request: the "Extract the
trusted gate baseline" step hard-exited 1 the moment the merge-base commit carried no baseline
blob at all, which is exactly the state of any pull request whose base branch predates this
baseline file, most obviously the pull request that introduces it. Because the evaluate step
downstream carries `if: always()`, it then also failed a second time, on a two-leg record the
paired measurement never got the chance to write. `tests/perf/README.md` had already documented an
absent trusted baseline as belonging in the same non-blocking `INCONCLUSIVE` vocabulary as every
other measurement-uncertainty condition; the shipped workflow did not implement that promise, and
the gap between what was documented and what actually ran stayed invisible until a real pull
request whose base branch had never carried the file actually existed to expose it.

This is now closed in code and under test. The evaluator carries a new `trusted-baseline-absent`
reason, structural and never retry-eligible since a re-measurement cannot make an absent baseline
file appear, reachable through a `--baseline-unavailable-reason` argument that resolves to a
non-blocking `INCONCLUSIVE` without ever opening `--record` or `--baseline`, so the outcome stays
robust even when the paired measurement also failed to produce a record. The workflow's extraction
step now records that reason and exits 0 instead of 1 when the blob is simply absent, while the
absent-versus-corrupt distinction this fix depends on is preserved exactly as before: a baseline
that is present at the merge base but corrupt, unparseable, or missing its `cells` mapping still
fails loudly with no verdict, pinned by its own test. The paired measurement step is deliberately
left running rather than skipped on this outcome, so this fix does not trade one open gap (a hard
failure with no verdict) for another (the mechanism never being observed end to end on a real pull
request). Stated plainly rather than implied: this fix has now been exercised both by unit tests proven to
fail against the unfixed code and pass against the fixed one, and by a real hosted run. GitHub
Actions run 32297377577, dispatched on the draft pull request that introduces this work, completed
in 14 minutes 13 seconds with every step succeeding, including the paired measurement that this fix
deliberately leaves running rather than skipped. The verdict it produced was `INCONCLUSIVE`, reason
`trusted-baseline-absent`, with zero gating cells evaluated: the absent-baseline condition is
structural and resolves before any per-cell evaluation runs, so every per-cell condition count,
including `metric-absent-from-leg` and `baseline-cell-missing`, reads zero on that run rather than
reflecting an absence of regressions. It is green rather than yellow because a non-blocking
inconclusive exits 0. This has been observed once, on one pull request, on one runner; it is not a
claim about behavior across a population of runs or across CPU models.

## Criteria and requirement reconciliation

Seven criteria this effort was accepted against, each named here in its own words rather than by a
requirement tag, since a reader of this repository has the code and the reports but not the tag
list.

1. **Zero spurious gating failures across enough unchanged-code runs to trust the number, with any
   uncertain outcome tracked separately from an actual failure.** **Met.** Ten real pull-request
   runs against changes that could not legitimately regress anything produced zero failing gating
   cells, matching the same result across thirty-seven earlier unchanged-code and unrelated-commit
   runs; the uncertain-outcome rate is tracked and reported on its own line rather than folded into
   the failure count, in both the earlier population and this one.
2. **Every deliberately seeded regression detected, with the smallest detectable magnitude reported
   per metric.** **Partially met.** Four of five seeded regressions were detected and attributed on
   real hosted records, each producing a first-tier exact-equality gating failure or, for the
   timing-only regression, a visible but deliberately non-gating wall-clock signal; the fifth,
   disabled frame batching, produced no usable sample on any of eleven hosted dispatches and was
   closed by an explicit, attributed override rather than a detection. Missing: a fix for that
   patch's own second, still-unidentified lock, and then a hosted dispatch that actually produces a
   clean sample so a magnitude can finally be computed.
3. **The gating job completes inside the ten minute wall-clock budget, including build, and any
   deep or long-running measurement runs in a workflow that cannot block a pull request.**
   **Partially met.** The deep-workflow half is fully met and machine-checkable: neither
   long-running measurement workflow declares a pull-request trigger anywhere in its own
   configuration. The wall-clock half is not true of every recorded run: thirteen of fourteen real
   gate dispatches stayed inside six hundred seconds, one exceeded it by eighty-three seconds for a
   dependency-mirror reason unrelated to the measurement itself, and the three runs demonstrating
   the trusted-baseline fix add one further overage of eighty-six seconds to the same open question.
   Missing: a recorded population of real dispatches with zero overages, which this project does
   not yet have.
4. **Everything runs entirely on GitHub-hosted general-purpose runners, never on self-hosted,
   bare-metal, or lab hardware.** **Met.** The capability matrix behind every tier decision was
   built entirely from hosted-runner evidence, and every workflow this record ships declares
   `ubuntu-24.04` as its only runner, with no self-hosted runner referenced anywhere.
5. **The existing published result format and history remain readable, and every change is
   additive.** **Met.** The published schema version was bumped once, a version-one record still
   parses and renders under the updated tooling with a test proving it against a real committed
   fixture, and the regenerated baseline and campaign artifacts were proven additive by a
   structural diff rather than assumed to be.
6. **Wall-clock throughput metrics are still collected and published, and still never gate.**
   **Met.** Every wall-clock metric this project published before this work continues to be
   collected and published; none of the 128 cells the gate actually blocks on is a wall-clock
   metric, and the tier rule that forbids it is enforced by construction in the metric registry,
   not by convention.
7. **A failure is self-explanatory: what regressed, by how much, which tier fired, and whether to
   believe it.** **Met.** A real blocking run's own step summary lists every failing cell, not only
   the first, each with its tier, its baseline sample count, its spread, its coefficient of
   variation, and its minimum detectable effect, so a developer can judge whether a regression is
   real before reaching for the escape hatch; a failing or uncertain outcome also carries a pointer
   to the contributor-facing documentation that explains what to do next.

Three requirement-level determinations fall short of fully met, restated here in their own words
rather than by a ledger tag, matching the same items already named above:

- The requirement that every seeded regression be detected. Missing: the same fix and the same
  follow-up dispatch named in criterion 2 above.
- The requirement that the smallest detected regression magnitude be reported per metric. Missing:
  the same fix, since no magnitude can be measured before a sample can be produced at all for the
  one regression that has never produced one.
- The requirement that the gating job complete inside the ten minute wall-clock budget. Missing:
  the same zero-overage population named in criterion 3 above.

No other determination behind either the seven criteria or the broader requirement set falls short
of fully met.

## Handoff

A maintainer picking this up after this record needs four things, roughly in the order they will
actually reach for them.

The one action no commit in this repository's history can perform: applying the branch-protection
setting above, on the base branch, naming the check by its exact frozen name. Nothing here does
that for a reason as much procedural as technical. It is a repository-settings action that
requires whoever holds admin access on the real target repository.

The entry point for any contributor whose own pull-request check goes red is
`tests/perf/README.md`, not this record: it documents the three verdicts, the escape hatch's exact
grammar, and the local reproduction procedure in a form written for that reader, one this record
deliberately does not duplicate.

This record itself is the empirical account: what shipped, why the paired same-job comparison was
chosen, what was measured to validate it, and what still does not close. A maintainer auditing a
claim in this record should expect every figure in it to be recomputed or independently traceable
rather than asserted, and the `## Inherited open gaps` list above to be read before treating
anything as fully closed.

The full raw measurement populations this record's own figures were recomputed from are not
carried in the shipped tree; they are reachable only through the published annotated tag recorded
in `docs/plans/perf-ci-hardening/gate-runs/evidence-tag.json`. A maintainer who needs to regenerate
a report or inspect a raw record this record does not retain a copy of starts there.
