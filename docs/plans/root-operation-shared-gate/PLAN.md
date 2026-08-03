# Root Operation Shared Gate Plan

## Goal

Extend `Root.operationLock()` so coordinated root operations exclude variable
and command entry points without serializing unrelated variable accesses during
normal operation.

## Proposed Model

- Root coordinated operations acquire exclusive access through the existing
  public `operationLock()` context manager.
- Variable `get`, `set`, `post`, and `write` entry points acquire shared access.
- Command execution acquires exclusive access. This lets command callbacks use
  `operationLock()` reentrantly without requiring a shared-to-exclusive lock
  upgrade.
- The exclusive owner may enter shared variable operations reentrantly.
- Once an exclusive waiter arrives, new shared entrants wait so a steady stream
  of variable traffic cannot starve a coordinated operation.
- Detached variables and commands continue to operate without a Root gate.

## Scope

- Add a private reentrant shared/exclusive gate owned by `Root`.
- Route `Root.operationLock()` through its exclusive side.
- Add private Node helpers for shared and exclusive entry.
- Guard concrete RemoteVariable, LocalVariable, LinkVariable, and command entry
  points.
- Add deterministic core tests for exclusion, shared concurrency, command
  reentrancy, and detached-node compatibility.
- Update operation-lock documentation to describe the expanded behavior.

## Important Boundary

For a variable call using `wait=False`, shared admission ends when the Python
method returns. The gate does not currently track the lifetime of an
asynchronous memory transaction after return. Existing block and transaction
locking remains responsible for that work.

## Validation

1. Run focused root/device I/O concurrency tests.
2. Run the nearest core variable and command tests.
3. Run Python compile and whitespace checks for edited files.
