.. _cookbook_advanced_stream_patterns:

================================
Advanced Stream Pattern Recipes
================================

Recipe entry points for advanced stream implementations:

- :doc:`/stream_interface/usingFifo`
- :doc:`/stream_interface/usingFilter`
- :doc:`/stream_interface/usingRateDrop`
- :doc:`/stream_interface/debugStreams`
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
- :doc:`/stream_interface/index`

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

- :doc:`/stream_interface/index`
- :doc:`/custom_module/index`

Recipe 3: Decouple receive callback with a worker thread
========================================================

Problem
=======

Frame processing in ``_acceptFrame`` is too heavy and introduces backpressure.

Procedure
=========

1. Keep ``_acceptFrame`` minimal: copy frame data + metadata, then enqueue.
2. Run a worker thread that dequeues and performs expensive processing.
3. Bound queue depth and drop/flag when overloaded.

Python pattern
==============

.. code-block:: python

   import queue
   import threading
   import numpy as np
   import rogue.interfaces.stream as ris

   class ThreadedRx(ris.Slave):
       def __init__(self, depth: int = 1024):
           super().__init__()
           self._q = queue.Queue(maxsize=depth)
           self._run = True
           self._thr = threading.Thread(target=self._worker, daemon=True)
           self._thr.start()

       def _acceptFrame(self, frame):
           with frame.lock():
               pkt = (
                   frame.getNumpy(),          # payload copy
                   frame.getChannel(),
                   frame.getError(),
                   frame.getFlags(),
               )

           try:
               self._q.put_nowait(pkt)
           except queue.Full:
               # Optional: count drops / log / set alarm
               pass

       def _worker(self):
           while self._run:
               try:
                   data, chan, err, flags = self._q.get(timeout=0.1)
               except queue.Empty:
                   continue
               self.process(data, chan, err, flags)
               self._q.task_done()

       def process(self, data: np.ndarray, chan: int, err: int, flags: int):
           # Expensive decode/analysis here
           pass

       def _stop(self):
           self._run = False
           self._thr.join(timeout=1.0)

Deep dive
=========

- :doc:`/stream_interface/receiving`
- :doc:`/stream_interface/frame_model`
