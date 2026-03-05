.. _pyrogue_core_model_api:

=========
Model API
=========

The model layer describes conversion between memory bit/byte representations and
Python-facing value semantics.

Why models matter
=================

- They separate protocol/storage representation from user-facing values.
- They keep conversion behavior reusable across related variables.
- They provide a consistent place for limits, formatting, and type mapping.

Model usage pattern
===================

1. Choose a model type that matches hardware encoding.
2. Attach it to variable/block definitions.
3. Validate read/write conversion behavior with representative values.

Boundary guidance
=================

Most users should first use tree-level variable abstractions. Drop to low-level
model details only when custom encoding or advanced mapping is required.

Conceptual docs:

- :doc:`/pyrogue_tree/model/index`
- :doc:`/pyrogue_core/model_types`

Reference docs:

- :doc:`/api/python/model`
- :doc:`/api/cpp/interfaces/memory/model`
