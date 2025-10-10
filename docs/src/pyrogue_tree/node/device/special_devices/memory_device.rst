.. _pyrogue_tree_node_device_memorydevice:

=========================
MemoryDevice Device Class
=========================

A special sub-class(named tuple) of Device, MemoryDevice, provides an alternative to creating a custom Device which uses _rawRead and _rawWrite calls.

* MemoryDevice allows values contained within a yaml configuration file to be written directly to memory, bypassing the normal Variables

   * Useful for large blocks of data which need to be written
   * Accesses can be non-contiguous
   * A MemoryDevice is write only

.. code-block:: python

   dev = MemoryDevice(name=None, offset = 0, size = 0,
                      wordBitSize=32, stride = 4,
                      base = pyrogue.UInt)

* Parameters:

   * wordBitSize: the size of each value in bits
   * stride: the spacing between the value locations in bytes
   * base: base class indicating the type of value contained in the memory

* The configuration yaml file is expected to contain a set of offsets and value

   * MemoryDeviceName:

      * 256: 0x12,0x13,0x14,0x15
      * 512: 0x22,0x23,0x24,0x25

* Results in the following address:values pairs being written to memory (wordBitSize=32, stride=4)

   * 256 = 0x12, 260 = 0x13, 264 = 0x14, 268 = 0x15
   * 512 = 0x22, 516 = 0x23, 520 = 0x24, 524 = 0x25

MemoryDevice Type Definition
============================

.. code-block:: python
   # MemoryDevice type
   MemoryDevice = namedtuple('MemoryDevice', ['name', 'offset', 'size', 'wordBitSize', 'stride', 'base'],
                          defaults=['DevName', 0x00000, 16, 8, 16, 'pr.Int'])