# Work Plans

Use this directory for planning, progress tracking, handoff, and decision
records for substantial feature work. These notes are repo-local working
documents for maintainers and AI agents; they are not part of the published
Sphinx site and are not a substitute for user-facing documentation, API docs,
tests, or final design docs.

Preferred layout:

```text
docs/plans/<task-name>/
  PLAN.md
  PROGRESS.md
  HANDOFF.md
  DECISIONS.md
  COMPLETED.md
```

Use the smallest useful set of files. A short task may only need `PLAN.md`;
long-running or interrupted work should include `PROGRESS.md` and `HANDOFF.md`.
`COMPLETED.md` is optional and should only exist when the completed work has
durable context worth preserving.

## File Purpose

- `PLAN.md`: scope, assumptions, affected subsystems, intended approach, and
  validation plan.
- `PROGRESS.md`: chronological status updates, completed work, commands run,
  results, blockers, and open questions.
- `HANDOFF.md`: current state, remaining tasks, known risks, verification gaps,
  and exact next steps for another agent or developer.
- `DECISIONS.md`: important tradeoffs or design decisions that should survive
  context resets.
- `COMPLETED.md`: concise final summary of completed work, validation,
  remaining follow-up, and links to permanent code, docs, tests, issues, or PRs.

## Lifecycle

Use `PROGRESS.md` and `HANDOFF.md` for active work. They should help another
agent or developer resume the task without reading an entire chat transcript.

When the task is complete:

- Keep `PLAN.md` only if it still explains useful scope or intent.
- Condense useful chronological details from `PROGRESS.md` into
  `COMPLETED.md` or `DECISIONS.md`; then delete `PROGRESS.md` if it is only a
  running log.
- Delete `HANDOFF.md` when there is no remaining handoff state.
- Keep `DECISIONS.md` if it records tradeoffs that are not obvious from the
  final code, tests, docs, issue, or PR.
- Add `COMPLETED.md` only when the completed task needs a durable final record.
  It should answer what changed, why the approach was chosen, what validation
  was done, what follow-up remains, and where the permanent artifacts live.
- Remove the whole task directory when it no longer carries durable value.

## Conventions

- Use a descriptive, stable task name, such as `tcp-memory-retry-cleanup` or
  `api-doc-refresh`.
- Keep notes concise and factual. Link to relevant files, tests, issues, or PRs
  when useful.
- Prefer summaries of long command output over pasted logs.
- Do not include secrets, credentials, private host details, or unrelated local
  environment noise.
- Keep status current when work spans multiple context windows.
- Completed records should be shorter than active records. Preserve decisions
  and final context, not every intermediate step.

For project-wide development guidance, read `../../DEVELOPMENT.md`.
