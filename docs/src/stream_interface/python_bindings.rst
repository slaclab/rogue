.. _stream_interface_python_bindings:

======================
Stream Python Bindings
======================

Python bindings expose stream modules into application-level scripts and tree
integration code.

When to use Python bindings
===========================

- Rapid bring-up and prototyping of stream topologies.
- Test harnesses and scripted validation flows.
- Hybrid systems where orchestration is in Python and hot paths are in C++.

Practical pattern
=================

1. Build and connect modules in Python for fast iteration.
2. Validate behavior and interfaces with realistic traffic.
3. Move only bottleneck stages to C++ when performance demands it.

See also :doc:`/stream_interface/example_pipelines` for workflow-oriented
examples.

Reference entry points:

- :doc:`/api/python/index`
- :doc:`/api/python/interfaces_stream_variable`
