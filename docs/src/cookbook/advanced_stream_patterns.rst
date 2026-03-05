.. _cookbook_advanced_stream_patterns:

================================
Advanced Stream Pattern Recipes
================================

Recipe entry points for advanced stream implementations:

- :doc:`/stream_interface/legacy_stream/usingFifo`
- :doc:`/stream_interface/legacy_stream/usingFilter`
- :doc:`/stream_interface/legacy_stream/usingRateDrop`
- :doc:`/stream_interface/legacy_stream/debugStreams`
- :doc:`/custom_module/index`

Recipe 1: Stabilize a bursty producer
=====================================

Problem
=======

Input bursts overwhelm downstream consumers and cause unstable latency.

Procedure
=========

1. Insert FIFO between producer and consumer.
2. Add RateDrop if bounded loss is acceptable.
3. Use debug stream instrumentation to verify queue and drop behavior.

Deep dive
=========

- :doc:`/stream_interface/built_in_modules`
- :doc:`/stream_interface/overview`

Recipe 2: Prototype then harden a custom stage
==============================================

Problem
=======

Need custom transformation logic without committing to C++ immediately.

Procedure
=========

1. Build topology and logic in Python bindings first.
2. Validate behavior on representative payloads and rates.
3. Migrate bottleneck stage to C++ while preserving external interfaces.

Deep dive
=========

- :doc:`/stream_interface/python_bindings`
- :doc:`/custom_module/index`
