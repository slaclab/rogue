# Root Operation Shared Gate Handoff

## Current State

The branch contains an uncommitted prototype of the shared/exclusive design.
Normal built-in variable accesses remain concurrent, queued exclusive
operations receive priority over new variable calls, and commands execute
exclusively with reentrant variable access.

## Review Points

1. Confirm that all command execution should be exclusive by default.
2. Confirm that acquiring `operationLock()` from inside a LocalVariable or
   LinkVariable callback should remain unsupported; coordinated callbacks must
   begin in an exclusive command or outer scope.
3. Decide whether roughly one microsecond of Python admission overhead on a hot
   cached LocalVariable read is acceptable or whether the gate should move to a
   lower-level implementation.
4. Decide whether downstream custom BaseVariable subclasses must be covered by
   a template-method refactor. The prototype guards Rogue's concrete built-in
   variable classes; an override that replaces `get` or `set` without calling
   the built-in implementation can bypass admission.
5. Clarify whether `wait=False` should gate only the Python API call, as in the
   prototype, or whether exclusivity must extend through asynchronous
   transaction completion.

## Suggested Next Validation

- Run the complete fast Python suite if the design points above are accepted.
- Run EPICS integration coverage on a host with the optional EPICS dependencies
  if end-to-end interface confirmation is desired.
- Add a perf-marked benchmark only if the project wants a maintained regression
  threshold for cached LocalVariable access.
