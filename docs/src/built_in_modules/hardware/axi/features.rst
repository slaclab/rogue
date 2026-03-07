.. _hardware_axi_features:

================================
Additional AxiStreamDma Features
================================

The following features are available in the AxiStreamDma class which
may be necessary for some operation modes.

All of these features are described in detail at :ref:`hardware_axi_axi_stream_dma`.

Kernel Module Debug
===================

Most of the lower level kernel modules which are used with the AxiStreamDma
class have a debugging mode. This can be enabled by the user with the following
calls:

In Python:

.. code-block:: python

   axiStream.setDriverDebug(True)

In C++:

.. code-block:: c

   axiStream->setDriverDebug(true);

The debug messages can then be viewed using the dmesg command in Linux:

.. code::

   $ dmesg

ZeroCopy Enable
===============

By default the AxiStreamDma class interacts with the underlying driver using
its zero copy buffer mode if available. The user's implementation may choose
to avoid this by asserting rogue::interface::memory::reqFrame() calls with
the zeroCopyEn flag set to false. 

Alternatively the zero copy mode can be disabled globally for all interactions
with the AxiStreamDma class using the following call:

In Python:

.. code-block:: python

   axiStream.setZeroCopyEn(False)

In C++:

.. code-block:: python

   axiStream->setZeroCopyEn(false);

DMA Acknowledge
===============

Some versions of the lower level driver and the underlying hardware will support
a DMA Acknowledge function which pulses a logic signal in the lower level firmware.
This was used in some experiments which need more complex handshakes between software
and firmware. The following method can be used to trigger this acknowledge. 

In Python:

.. code-block:: python

   axiStream.dmaAck()

In C++:

.. code-block:: c

   axiStream->dmaAck();

Frame Send Timeout
==================

In some cases the lower level driver will not be ready when allocating new
buffers or sending frames. After a defined timeout the AxiStreamDma class 
will generate a warning message but continue to wait for the driver. The following
method will adjust the period between warning messages. The passed value is the
timeout period in microseconds.

In Python:

.. code-block:: python

   axiStream.setTimeout(1500)

In C++:

.. code-block:: c

   axiStream->setTimeout(1500);

