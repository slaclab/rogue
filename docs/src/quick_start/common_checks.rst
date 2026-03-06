.. _quick_start_common_checks:

=====================
Common Quick Checks
=====================

Use this page to quickly confirm your setup before moving to deeper tutorials.

Environment checks
==================

- ``import pyrogue`` succeeds.
- Installed version is visible from ``rogue.Version.current()``.

Runtime checks
==============

- Root can be instantiated and entered/exited.
- At least one variable read works.
- At least one command invocation works.

Client checks
=============

- Simple client connectivity succeeds: :doc:`/pyrogue_tree/client_interfaces/simple`
- Optional virtual client path behaves as expected: :doc:`/pyrogue_tree/client_interfaces/virtual`

If checks fail
==============

- Revisit installation steps: :doc:`/installing/index`
- Review root-level concepts: :doc:`/pyrogue_tree/node/root/index`
- Review client connectivity: :doc:`/pyrogue_tree/client_interfaces/index`
