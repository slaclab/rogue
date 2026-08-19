# gh CLI Smoke Test

Recorded outcomes of the three `gh` operations the campaign driver depends on, run for
real against the fork `ruck314/rogue` with the `gh` binary actually installed on this
machine. Recorded as observed behavior of this exact version, not as documentation for
a newer release.

## Installed version

```
gh version 2.4.0+dfsg1 (2022-03-23 Ubuntu 2.4.0+dfsg1-2)
https://github.com/cli/cli/releases/latest
```

## Available `--json` fields

`gh run list --json bogusfield` rejects an unrecognized field with a self-documenting
error listing every field this version supports:

```
Unknown JSON field: "bogusfield"
Available fields:
  conclusion
  createdAt
  databaseId
  event
  headBranch
  headSha
  name
  status
  updatedAt
  url
  workflowDatabaseId
```

Exit code: `1`. This is the complete field set; there is no `displayTitle`, `jobs`, or
`headRepository` field at this version. A later driver script must be written against
exactly this list.

## `gh workflow run`

Command:

```sh
gh workflow run perf_probe.yml --repo ruck314/rogue --ref perf-probe/campaign
```

- Exit code: `0`
- stdout: empty
- stderr: empty

This version prints neither a run identifier nor a run URL on a successful dispatch.
Verdict: **pass** (the workflow ran), but the driver must correlate the resulting run
afterward via `gh run list --json`, filtered by `event == "workflow_dispatch"`,
`headBranch`, and `createdAt` shortly after the dispatch call, since dispatch itself
gives no direct handle back to the run it started.

## `gh run list`

Command:

```sh
gh run list --repo ruck314/rogue \
  --json databaseId,headSha,headBranch,createdAt,event,workflowDatabaseId,status,conclusion \
  --limit 20
```

- Exit code: `0`
- Runs returned: 2 (the push-triggered run from the end-to-end proof, plus the
  `workflow_dispatch` run above)
- The dispatched run was identified by `event == "workflow_dispatch"`, `headBranch ==
  "perf-probe/campaign"`, and a `createdAt` timestamp within a few seconds of the
  dispatch call. `databaseId` for that run fed directly into the download step below.

Verdict: **pass**.

## `gh run download`

Command:

```sh
gh run download <run-id> --repo ruck314/rogue -n probe-results-1 -D <temporary directory>
```

- Exit code: `0`
- Files retrieved: 1 (`probe-1.json`)
- Total byte count: 3540 bytes

The temporary directory was deleted immediately after recording the above; this file is
the committed evidence, not a second copy of the artifact.

Verdict: **pass**.

## Unsupported at this version

- `gh run list --json` has no `displayTitle`, `jobs`, `headRepository`, or any field
  beyond the eleven listed above.
- `gh workflow run` has no flag or output mode that returns a run identifier or URL; a
  driver must always correlate via `gh run list --json` afterward.
- `gh run view --json jobs` is also rejected with the same field-enumeration error at
  this version (not independently re-verified in this session against the fork, per the
  research finding already recorded for `slaclab/rogue`; the `gh run list` field set
  above is what this session's live calls exercised).
