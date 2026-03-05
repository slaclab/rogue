.. _pyrogue_core_polling:

=======
Polling
=======

Polling behavior in a PyRogue application is orchestrated by root-level polling
queues and variable poll intervals.

Polling strategy
================

- Poll only values that change over time and are operationally important.
- Keep fast and slow update classes on separate poll intervals where possible.
- Avoid aggressive polling on high-latency links unless required.

Common pattern
==============

1. Assign poll intervals by value volatility and operator need.
2. Validate update rate under realistic network and load conditions.
3. Promote exceptions to event-driven or explicit command reads when needed.

Related topics
==============

- Tree structure and variable placement: :doc:`/pyrogue_core/tree_architecture`
- Client-facing behavior: :doc:`/pyrogue_core/client_access`

Primary reference page:

- :doc:`/pyrogue_tree/node/root/poll_queue`

API reference:

- :doc:`/api/python/pollqueue`
- :doc:`/api/python/root`
