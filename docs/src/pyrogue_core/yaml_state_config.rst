.. _pyrogue_core_yaml_state_config:

===============================
YAML: Configuration and State
===============================

PyRogue supports YAML-based workflows for saving and restoring configuration and
state from tree objects.

Typical YAML workflows
======================

- Configuration baselines for known-good startup values.
- Captured runtime state for debug and issue reproduction.
- Status snapshots for validation and operator handoff.

Practical guidance
==================

- Separate baseline configuration from transient runtime state.
- Track YAML files in source control when they represent release artifacts.
- Document version compatibility when schema or naming changes occur.

Related tasks
=============

- First setup and validation: :doc:`/quick_start/index`
- End-to-end integration workflow: :doc:`/tutorials/system_integration_tutorial`

Start from root/device usage pages:

- :doc:`/pyrogue_tree/node/root/index`
- :doc:`/pyrogue_tree/node/device/index`

API reference:

- :doc:`/api/python/root`
- :doc:`/api/python/device`
