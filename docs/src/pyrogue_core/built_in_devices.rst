.. _pyrogue_core_built_in_devices:

================
Built-in Devices
================

Rogue includes a set of built-in device classes for common data paths and
control tasks.

What belongs here
=================

Built-in devices provide prepackaged behavior for common integration tasks such
as data capture, file writing, stream bridging, and run-control orchestration.

Selection guidance
==================

- Choose built-in devices first when they match your data/control pattern.
- Wrap with custom ``Device`` classes only when system-specific behavior is
  needed.
- Keep user-facing variable/command names stable across wrappers.

Integration pattern
===================

1. Add built-in device under the appropriate subtree.
2. Wire it to stream and/or memory interfaces as needed.
3. Expose operational control via variables/commands.
4. Validate behavior with quick-start and tutorial checks.

Device guides:

- :doc:`/pyrogue_tree/node/device/special_devices/data_receiver`
- :doc:`/pyrogue_tree/node/device/special_devices/data_writer`
- :doc:`/pyrogue_tree/node/device/special_devices/stream_reader`
- :doc:`/pyrogue_tree/node/device/special_devices/stream_writer`
- :doc:`/pyrogue_tree/node/device/special_devices/run_control`
- :doc:`/pyrogue_tree/node/device/special_devices/process`

API reference:

- :doc:`/api/python/datareceiver`
- :doc:`/api/python/datawriter`
- :doc:`/api/python/runcontrol`
- :doc:`/api/python/process`
