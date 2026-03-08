.. _hardware:
.. _built_in_modules_hardware:

========
Hardware
========

Hardware modules are the concrete device-facing endpoints used to connect Rogue
to PCIe cards and DMA-capable data paths. They provide the low-level bridge
from host software into firmware stream and memory channels.

These modules are generally selected first by hardware platform and driver
availability, then paired with Protocol modules to define link semantics.

The driver stack required to use these interfaces is available at:

https://github.com/slaclab/aes-stream-drivers

After choosing a hardware endpoint, continue with
:doc:`/built_in_modules/protocols/index` to select transport/framing behavior,
and with :doc:`/stream_interface/index` or :doc:`/memory_interface/index`
depending on data path type.

.. toctree::
   :maxdepth: 1
   :caption: Hardware:

   axi/index

   raw/index
