# Root Operation Shared Gate Decisions

## Shared Variable Access

Normal variable calls use shared admission instead of the same mutex used by
exclusive operations. This preserves concurrency between unrelated hardware or
local-variable accesses while still allowing a coordinated operation to wait
for active calls to finish and block new calls.

## Exclusive Commands

Commands use exclusive admission. Commands commonly coordinate multiple
variables and may explicitly acquire `operationLock()` in application code.
Making command entry exclusive avoids an implicit shared-to-exclusive upgrade,
which is difficult to make both atomic and deadlock-free.

## Writer Preference

New top-level shared entrants wait behind a queued exclusive operation. Nested
shared calls by an existing reader are allowed to finish so callbacks and link
variables cannot deadlock merely because a writer arrived.

## No Implicit Upgrade

Acquiring `operationLock()` from inside a shared variable callback is not part
of the supported model. Coordinated application behavior should begin at a
command or an explicit exclusive scope, then call variables reentrantly.
