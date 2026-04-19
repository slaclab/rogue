.. _protocols_rocev2_classes_server:

======
Server
======

``Server`` is the RC QP receive server. It inherits ``Core`` for the
ibverbs resources and inherits ``rogue::interfaces::stream::Master`` and
``rogue::interfaces::stream::Slave`` so it participates in the Rogue stream
graph. A background thread polls the completion queue and re-posts receive
work requests as downstream consumers release frames (zero-copy slab).

For conceptual guidance, see :doc:`/built_in_modules/protocols/rocev2/index`.


Threading and Lifecycle
-----------------------

- The constructor allocates the slab, MR, CQ, and RC QP and transitions
  the QP to ``INIT``. It does **not** spawn the background poll thread.
- The receive thread is started by ``completeConnection()`` once the
  FPGA QPN is known and the QP has been moved to ``RTR`` / ``RTS``. It
  is stopped by ``stop()`` or the destructor.
- The poll thread holds ``rogue::GilRelease`` across blocking ibverbs
  calls.
- ``IBV_WC_WR_FLUSH_ERR`` exits the thread cleanly instead of spin-looping.
- An ibverbs failure inside ``postRecvWr()`` is caught inside the poll
  thread; the thread logs the error and exits cleanly instead of
  escaping the thread entry point and triggering ``std::terminate``.


Python binding
--------------

This C++ class is also exported into Python as
``rogue.protocols.rocev2.Server``.

Python API page:

- :doc:`/api/python/rogue/protocols/rocev2/server`


Class Reference
---------------

.. cpp:class:: rogue::protocols::rocev2::Server : public rogue::protocols::rocev2::Core, public rogue::interfaces::stream::Master, public rogue::interfaces::stream::Slave

   RC Queue Pair receive server. Owns the Completion Queue (CQ), Queue
   Pair (QP, type ``IBV_QPT_RC``), and Memory Region (MR), runs the RX
   completion-queue polling thread, and re-posts receive work requests
   as frames are returned by downstream consumers (zero-copy slab).

   .. cpp:function:: static std::shared_ptr<Server> create(const std::string& deviceName, uint8_t ibPort, uint8_t gidIndex, uint32_t maxPayload = 9000, uint32_t rxQueueDepth = 256)

      Factory method. Returns a shared pointer to a new ``Server``.

      :param deviceName: ibverbs device name (e.g. ``rxe0``, ``mlx5_0``)
      :param ibPort: ibverbs port number (almost always ``1``)
      :param gidIndex: GID table index for the host NIC's RoCEv2 entry
      :param maxPayload: maximum bytes per RDMA WRITE (default: 9000)
      :param rxQueueDepth: number of pre-posted receive slots (default: 256)
      :returns: ``ServerPtr`` (shared pointer to the new server)

   .. cpp:function:: Server(const std::string& deviceName, uint8_t ibPort, uint8_t gidIndex, uint32_t maxPayload, uint32_t rxQueueDepth)

      Constructor. Allocates the slab memory region, registers it with the
      HCA, creates the CQ and RC QP, and transitions the QP to ``INIT``.
      The receive thread is **not** started here — it is spawned later by
      ``completeConnection()`` after the FPGA QPN is known. Throws
      ``rogue::GeneralError`` on ibverbs failures; partial-init resources
      are released before the throw propagates.

   .. cpp:function:: ~Server()

      Calls ``stop()``; ``stop()`` releases the slab MR and CQ/QP
      resources, and the inherited ``Core`` destructor releases the PD
      and ibverbs context.

   .. cpp:function:: void stop()

      Signals the receive thread to exit, joins and deletes it, then
      releases the ibverbs resources owned by ``Server``: destroys the
      QP and CQ, deregisters the MR, and frees the slab. Idempotent —
      safe to call multiple times (also called by ``~Server()``).

   .. cpp:function:: void setFpgaGid(const std::string& gidBytes)

      :param gidBytes: 16-byte FPGA GID (IPv4-mapped IPv6) as a raw byte string

      MUST be called before ``completeConnection()``.

   .. cpp:function:: void completeConnection(uint32_t fpgaQpn, uint32_t fpgaRqPsn, uint32_t pmtu = 5, uint32_t minRnrTimer = 1)

      Transitions the QP from ``INIT`` to ``RTR`` and then ``RTS`` using
      the FPGA's QPN and RQ PSN.

      :param fpgaQpn: FPGA QP number (24-bit)
      :param fpgaRqPsn: FPGA receive-queue starting PSN
      :param pmtu: Path MTU enum (1=256, 2=512, 3=1024, 4=2048, 5=4096; default: 5)
      :param minRnrTimer: IB-spec RNR timer code (1=0.01ms, 14=1ms, 18=4ms, 22=16ms, 31=491ms; default: 1)

   .. cpp:function:: uint32_t getQpn() const

      :returns: Host RC QP number (24-bit).

   .. cpp:function:: std::string getGid() const

      :returns: Host GID as a colon-separated 8-group hex string (NIC RoCEv2 address).

   .. cpp:function:: uint32_t getRqPsn() const

      :returns: Host receive-queue starting PSN. The FPGA's send-queue PSN must match this.

   .. cpp:function:: uint32_t getSqPsn() const

      :returns: Host send-queue starting PSN. The FPGA's receive-queue PSN must match this.

   .. cpp:function:: uint64_t getMrAddr() const

      :returns: Host MR virtual base address. The FPGA RDMA-WRITEs at this address.

   .. cpp:function:: uint32_t getMrRkey() const

      :returns: Host MR rkey. Hand this to the FPGA so it can target the host MR.

   .. cpp:function:: uint64_t getFrameCount() const

      :returns: Total frames received since construction.

   .. cpp:function:: uint64_t getByteCount() const

      :returns: Total bytes received since construction.

   .. cpp:function:: void acceptFrame(rogue::interfaces::stream::FramePtr frame) override

      ``stream::Slave`` override. RoCEv2 RX is currently one-directional
      (FPGA-to-host); ``acceptFrame()`` is intentionally a no-op for v1
      (TX support is tracked in FUT-01).

   .. cpp:function:: static void setup_python()

      Registers the ``rogue.protocols.rocev2.Server`` Boost.Python class
      and inherited-base conversions to ``CorePtr``, ``MasterPtr``, and
      ``SlavePtr``. Called by ``module.cpp``.


Type Aliases
------------

.. cpp:type:: ServerPtr = std::shared_ptr<rogue::protocols::rocev2::Server>

   Shared-pointer alias used throughout ``rogue::protocols::rocev2``.
