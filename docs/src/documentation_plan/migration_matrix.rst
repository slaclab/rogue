.. _documentation_plan_migration_matrix:

================
Migration Matrix
================

This matrix tracks where content is moving as the revamp proceeds.

.. list-table:: Migration Matrix
   :header-rows: 1
   :widths: 34 28 10 10 14

   * - Old Path
     - New Path
     - Action
     - Owner
     - Milestone
   * - /getting_started/index
     - /quick_start/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /getting_started/pyrogue_tree_example/*
     - /tutorials/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /pyrogue_tree/index
     - /pyrogue_tree/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /interfaces/stream/index
     - /stream_interface/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /interfaces/memory/index
     - /memory_interface/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /utilities/*, /hardware/*, /protocols/*
     - /built_in_modules/index
     - Link
     - Docs Team
     - M2 IA [done]
   * - /interfaces/clients/*, /interfaces/pyrogue/*
     - /pyrogue_tree/index
     - Move
     - Docs Team
     - M2 IA [done]
   * - /interfaces/stream/*
     - /stream_interface/index
     - Move
     - Docs Team
     - M2 IA [done]
   * - /interfaces/memory/*
     - /memory_interface/index
     - Move
     - Docs Team
     - M2 IA [done]
   * - /interfaces/stream/index narrative
     - /stream_interface/index
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/memory/index narrative
     - /memory_interface/index
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/clients/index narrative
     - /pyrogue_tree/client_interfaces/index
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/pyrogue/index narrative
     - /pyrogue_tree/client_interfaces/index
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/simulation/index narrative
     - /built_in_modules/integrations
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/version narrative
     - /built_in_modules/integrations
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/sql narrative
     - /built_in_modules/integrations
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /utilities/index narrative
     - /built_in_modules/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /hardware/index narrative
     - /built_in_modules/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/index narrative
     - /built_in_modules/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /installing/index narrative
     - /installing/index
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - /logging/index narrative
     - /logging/index
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - /pydm/index narrative
     - /pydm/index
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - /interfaces/simulation/mememulate placeholder
     - /built_in_modules/integrations
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/simulation/pgp2b placeholder
     - /built_in_modules/integrations
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/simulation/sideband placeholder
     - /built_in_modules/integrations
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/udp/index placeholder
     - /protocols/udp/index
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/udp/client placeholder
     - /protocols/udp/client
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/udp/server placeholder
     - /protocols/udp/server
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/packetizer/index placeholder
     - /protocols/packetizer/index
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/packetizer/core placeholder
     - /protocols/packetizer/core
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/packetizer/coreV2 placeholder
     - /protocols/packetizer/coreV2
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/epicsV4/index placeholder
     - /protocols/epicsV4/index
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/uart placeholder
     - /protocols/uart
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /api/cpp/protocols/udp/* placeholder
     - /api/cpp/protocols/udp/*
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /api/cpp/protocols/packetizer/* placeholder
     - /api/cpp/protocols/packetizer/*
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /migration/rogue_v6 TBD links
     - /migration/rogue_v6
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/memory/hub TBD links
     - /memory_interface/hub
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /api/cpp/interfaces/memory/transaction
     - /memory_interface/transactions
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /advanced_examples/index
     - /cookbook/index
     - Link
     - Docs Team
     - M3 Coverage [done]
   * - /custom_module/index
     - /stream_interface/index
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /quick_start first-success and checks content
     - /quick_start/first_success_path and /quick_start/common_checks
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /tutorials workflow content
     - /tutorials/device_workflow_tutorial and /tutorials/system_integration_tutorial
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/udp narrative expansion
     - /protocols/udp/index, /protocols/udp/client, /protocols/udp/server
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/packetizer narrative expansion
     - /protocols/packetizer/index, /protocols/packetizer/core, /protocols/packetizer/coreV2
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /api/cpp/protocols/udp placeholder wrapper cleanup
     - /api/cpp/protocols/udp/index, /api/cpp/protocols/udp/core, /api/cpp/protocols/udp/client, /api/cpp/protocols/udp/server
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /api/cpp/protocols/packetizer placeholder wrapper cleanup
     - /api/cpp/protocols/packetizer/index, /api/cpp/protocols/packetizer/core, /api/cpp/protocols/packetizer/coreV2, /api/cpp/protocols/packetizer/controller, /api/cpp/protocols/packetizer/controllerV1, /api/cpp/protocols/packetizer/controllerV2, /api/cpp/protocols/packetizer/application, /api/cpp/protocols/packetizer/transport
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/epicsV4 and /protocols/uart narrative expansion
     - /protocols/epicsV4/index and /protocols/uart
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/srp narrative expansion
     - /protocols/srp/index, /protocols/srp/srpV0, /protocols/srp/srpV3, /protocols/srp/cmd
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/rssi narrative expansion
     - /protocols/rssi/index, /protocols/rssi/client, /protocols/rssi/server
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/batcher narrative expansion
     - /protocols/batcher/index, /protocols/batcher/inverter, /protocols/batcher/splitter
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/xilinx narrative expansion
     - /protocols/xilinx/index
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /protocols/epics narrative expansion
     - /protocols/epicsV4/index, /protocols/epicsV4/epicspvholder, /protocols/epicsV4/epicspvserver
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /pyrogue_core narrative expansion
     - /pyrogue_tree/index, /pyrogue_tree/client_interfaces/index, /pyrogue_tree/core/variable, /pyrogue_tree/core/poll_queue, /pyrogue_tree/core/yaml_configuration, /pyrogue_tree/core/model, /pyrogue_tree/builtin_devices/index, /cookbook/advanced_pyrogue_patterns
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /stream_interface narrative expansion
     - /stream_interface/index, /stream_interface/built_in_modules, /stream_interface/example_pipelines, /stream_interface/python_bindings
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /api/python/index regroup by role
     - /api/python/index
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /cookbook recipe expansion
     - /cookbook/index, /cookbook/pyrogue_devices_and_variables, /cookbook/advanced_stream_patterns
     - Split
     - Docs Team
     - M3 Coverage [done]
   * - /interfaces/index broad conceptual narrative
     - /pyrogue_tree/index, /stream_interface/index, /memory_interface/index
     - Move
     - Docs Team
     - M3 Coverage [done]
   * - /logging/*, /pydm/*, /installing/*
     - /logging/index, /pydm/index, /installing/index
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - /pyrogue_core, /stream_interface, /memory_interface toctree legacy-path cleanup
     - /pyrogue_tree/index, /stream_interface/index, /memory_interface/index
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Top-level nav dedupe for operations topics
     - /introduction/index and /documentation_index
     - Move
     - Docs Team
     - M4 Harmonization [done; superseded by decision reversal]
   * - Top-level operations nav decision reversal
     - /introduction/index and /documentation_index (restore /installing/index, /logging/index, /pydm/index as top-level)
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Landing-page terminology and ordering harmonization
     - /introduction/index, /documentation_index, /built_in_modules/index
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Re-home legacy interface index pages to canonical section toctrees
     - /pyrogue_tree/index, /stream_interface/index, /memory_interface/index
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Move interface client/pyrogue docs into canonical tree/client-interface sections
     - /interfaces/clients/* -> /pyrogue_tree/client_interfaces/*; /interfaces/pyrogue/zmq_server -> /pyrogue_tree/client_interfaces/zmq_server; remaining /interfaces/pyrogue/* -> /pyrogue_tree/client_interfaces/*
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Move interface stream/memory docs into canonical section trees
     - /interfaces/stream/* -> /stream_interface/*; /interfaces/memory/* -> /memory_interface/*
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Integrate legacy stream subfolder into parent stream narrative
     - /stream_interface/legacy_stream/* -> /stream_interface/* (folder removed)
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Integrate legacy memory subfolder into parent memory narrative
     - /memory_interface/legacy_memory/* -> /memory_interface/* (folder removed)
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Built-in modules routing-page cleanup and simulation narrative integration
     - /built_in_modules/index (expanded); removed /built_in_modules/overview and /built_in_modules/integrations; expanded /built_in_modules/simulation/* and /built_in_modules/sql
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Move remaining interface integration pages into canonical sections
     - /interfaces/simulation/\* -> /built_in_modules/simulation/\*; /interfaces/sql -> /built_in_modules/sql; /interfaces/version -> /built_in_modules/version; /interfaces/cpp_api -> /built_in_modules/cpp_api_wrapper
     - Move
     - Docs Team
     - M4 Harmonization [done]
   * - Remove interfaces transitional index from primary navigation
     - /introduction/index and canonical section landing pages
     - Move
     - Docs Team
     - M4 Harmonization [done]

Status keys:

- Link: new section points to existing content.
- Move: narrative content moved to new canonical page.
- Split: existing page split into conceptual/how-to/reference pages.

Execution guardrail for current phase:

- Narrative can be revised, cleaned up, and expanded.
- If narrative is no longer a good fit, mark it explicitly and track relocation.

Deferred API Reorg Notes
========================

- Python API regrouping around core roles (including ``Model`` and model
  subclasses) is complete in ``/api/python/index``.

Deferred Content Expansion Notes
================================

- Expand cookbook breadth with additional recipes for polling, YAML workflows,
  built-in devices, and stream transport integration.
- Expand stream/threading cookbook coverage: threaded receive workers, queue
  backpressure policies, shutdown/lifecycle-safe worker patterns, and C++
  analogs.
- Continue protocol/API cross-link hardening where narrative-to-reference
  boundaries are still rough.
