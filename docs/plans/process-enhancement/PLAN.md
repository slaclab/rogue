# Process pause/resume (#1292)

- Build on the stopped-status fix (#1291) already committed on this branch.
- Add cooperative `Pause`, `Resume`, `Paused`, and `pausePoint(publish=None)`.
  Use a separate Resume command, preserving Start's new-run semantics.
- Reuse the plain Process lock through a condition; do not hold it while
  invoking a publication callback or joining a worker.
- Acknowledge pause only at a checkpoint; wake on resume or stop; clear pause
  state on every worker exit. Preserve worker state and progress while paused.
- Keep Paused polling consistent with other status variables (1 second), and
  explicitly flush checkpoint updates so listeners see them while blocked.
- Cover pause/resume, pending cancellation, stop/shutdown, error cleanup,
  restart, callbacks without checkpoints, and snapshot visibility with
  deterministic thread coordination. Run Process/config tests and build docs
  in the existing Miniforge rogue_build environment.
- User authorized committing and pushing the validated changes to draft PR #1296.
