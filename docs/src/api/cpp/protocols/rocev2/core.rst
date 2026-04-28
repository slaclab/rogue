.. _protocols_rocev2_classes_core:

====
Core
====

``Core`` opens the ibverbs device and allocates the shared protection
domain (PD) that ``Server`` builds on top of. The completion queue (CQ),
queue pair (QP, type ``IBV_QPT_RC``), and memory region (MR) are owned
by ``Server``, not ``Core``.

For conceptual guidance, see :doc:`/built_in_modules/protocols/rocev2/index`.


Python binding
--------------

This C++ class is also exported into Python as
``rogue.protocols.rocev2.Core``.

Python API page:

- :doc:`/api/python/rogue/protocols/rocev2/core`


Class Reference
---------------

.. cpp:class:: rogue::protocols::rocev2::Core

   Opens the ibverbs device and allocates the shared protection domain.
   Subclassed by ``Server``, which adds the CQ / QP (type ``IBV_QPT_RC``)
   / MR resources on top.

   .. cpp:function:: Core(const std::string& deviceName, uint8_t ibPort, uint8_t gidIndex, uint32_t maxPayload = 9000)

      :param deviceName: ibverbs device name (e.g. ``rxe0`` for SoftRoCE, ``mlx5_0`` for a Mellanox/NVIDIA NIC)
      :param ibPort: ibverbs port number (almost always ``1``)
      :param gidIndex: GID table index for the host NIC's RoCEv2 IPv4/IPv6 entry
      :param maxPayload: maximum bytes per RDMA WRITE (default: ``DefaultMaxPayload`` = 9000)

   .. cpp:function:: virtual ~Core()

      Deallocates the protection domain and closes the ibverbs context.
      The CQ, QP, and MR (owned by ``Server``) must already have been
      released by ``Server::stop()`` before this destructor runs.

   .. cpp:function:: uint32_t maxPayload() const

      :returns: Configured maximum payload size in bytes.

   .. cpp:function:: static void setup_python()

      Registers the ``rogue.protocols.rocev2.Core`` Boost.Python class and
      exposes the module-level constants ``DefaultMaxPayload`` and
      ``DefaultRxQueueDepth``. Called by ``module.cpp``.


Type Aliases
------------

.. cpp:type:: CorePtr = std::shared_ptr<rogue::protocols::rocev2::Core>

   Shared-pointer alias used throughout ``rogue::protocols::rocev2``.


Module Constants
----------------

.. cpp:var:: static const uint32_t DefaultRxQueueDepth = 256

   Default number of receive work requests to keep posted at all times.

.. cpp:var:: static const uint32_t DefaultMaxPayload = 9000

   Default maximum transfer unit for a single RDMA WRITE (jumbo-frame
   equivalent).
