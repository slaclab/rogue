# Root/Device Default Verification Plan

## Scope

Implement issue #1285 by allowing a Root or Device to provide the default
write-verification setting for descendant RemoteVariables.

## Behavior

- An explicit `RemoteVariable(verify=True|False)` has highest precedence.
- Otherwise, use the nearest `Device(defaultVerify=...)` setting.
- Otherwise, use `Root(defaultVerify=...)`.
- Preserve the historical default of verification enabled.
- Resolve inheritance before memory Blocks build; do not support runtime
  verify-mask changes.

## Validation

- Test Root inheritance, Device override, and explicit-variable precedence.
- Test that disabling the inherited default suppresses the Verify transaction.
- Run the focused core tests and project linters.
