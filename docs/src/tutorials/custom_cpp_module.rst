.. _tutorial_custom_cpp_module:

===========================
Extend Rogue With C++
===========================

Python is fast enough for most stream work, because the heavy lifting already
happens in Rogue's C++ core. But when a per-frame transform sits in the data
path at high rate, the Python callback becomes the bottleneck — and the fix is to
write that stage in C++ and expose it to Python.

This tutorial builds a working C++ stream module, loads it into Python, and wraps
it in a ``Device``. Rather than inventing new code, it walks the module Rogue's
own continuous integration compiles as a downstream build test, so the source is
guaranteed to work.

.. note::

   **No hardware required.** The module is a pure stream transform, driven by a
   Python source and sink.

Prerequisites
=============

Finish :doc:`/getting_started/index`, and read
:doc:`/stream_interface/sending` and :doc:`/stream_interface/receiving` — the C++
class implements the same ``Master`` and ``Slave`` roles in native code.

You also need a C++ toolchain (``g++``), ``cmake``, and a Rogue installation
built with Python support.

The Module
==========

The source lives at ``tests/downstream/src/BitInverter.cpp`` in the Rogue
repository. It inverts every payload byte (``byte ^ 0xFF``) and forwards the
result downstream, subclassing both ``Master`` and ``Slave`` so it can sit in the
middle of a pipeline.

Four patterns in that file are worth understanding, because every custom module
repeats them:

* A static ``create()`` factory returns a ``std::shared_ptr``. That is the
  ownership model Rogue uses throughout its graph — never construct these
  objects on the stack.
* ``acceptFrame()`` is the single ingress hook. It takes the frame lock, walks
  the payload with a ``FrameIterator`` (which transparently spans the frame's
  underlying buffers), mutates bytes in place, releases the lock, and calls
  ``sendFrame()`` inherited from ``Master``.
* The Python bindings are guarded by ``#ifndef NO_PYTHON``, so the same source
  compiles into a Python-free C++ build.
* ``BOOST_PYTHON_MODULE`` registers the bindings. Rogue manages the GIL in its
  own bindings, so no explicit thread initialisation is needed.

The full annotated source is in :doc:`/custom_module/sourcefile`.

Building It
===========

``find_package(Rogue)`` supplies the include paths and libraries. Configure
against the Rogue installation you will **import from** — see
:ref:`tutorial_custom_cpp_module_troubleshooting` for why that matters:

.. code-block:: bash

   cd tests/downstream
   cmake -B build \
       -DCMAKE_PREFIX_PATH=$CONDA_PREFIX \
       -DCMAKE_SHARED_LINKER_FLAGS="-L$CONDA_PREFIX/lib"
   cmake --build build

The linker flag is needed because ``RogueConfig.cmake`` lists the core library
by bare name (``rogue-core``) without a search path, so the linker fails with
``cannot find -lrogue-core`` unless you supply one. If your Rogue lives
somewhere other than a conda environment, substitute that prefix in both places.

This produces ``BitInverter.so``. Put its directory on ``PYTHONPATH``, and make
sure the Rogue library is findable at run time:

.. code-block:: bash

   export PYTHONPATH=$PWD/build:$PYTHONPATH
   export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

Using It From Python
====================

The compiled class behaves exactly like a built-in stream module — it connects
with ``>>`` and needs no wrapper to function. Drive it with a Python source and
sink:

.. literalinclude:: examples/custom_cpp_module_check.py
   :language: python
   :pyobject: ByteSource

.. literalinclude:: examples/custom_cpp_module_check.py
   :language: python
   :pyobject: ByteCapture

Then put the C++ module between them:

.. literalinclude:: examples/custom_cpp_module_check.py
   :language: python
   :pyobject: invertThroughModule

.. code-block:: text

   input  : 000fff
   output : fff000
   correct: True

``0x00`` became ``0xFF``, ``0x0F`` became ``0xF0``, ``0xFF`` became ``0x00``.
A Python ``Master`` fed a C++ transform which fed a Python ``Slave`` — mixing
languages freely in one pipeline is the point of the binding layer.

Wrapping It In A Device
=======================

The C++ object is a stream endpoint, not a ``Device``, so it has no place in a
tree by itself. A thin wrapper gives it a name, a description, and somewhere to
expose status:

.. literalinclude:: examples/custom_cpp_module_check.py
   :language: python
   :pyobject: BitInverterDevice

The ``__rshift__``/``__lshift__`` overrides let the wrapper stand in for the raw
object inside a ``a >> wrapper >> b`` chain, so tree membership does not cost you
the connection syntax. :doc:`/custom_module/wrapper` covers richer wrappers that
surface C++ counters as PyRogue variables.

.. _tutorial_custom_cpp_module_troubleshooting:

Troubleshooting
===============

Two failures are worth calling out, because both produce errors that do not
obviously point at their cause.

**"extension class wrapper ... has not been created yet"**

.. code-block:: text

   RuntimeError: extension class wrapper for base class
   rogue::interfaces::stream::Master has not been created yet

The module was compiled against one Rogue installation and imported alongside a
different one. Boost.Python registers a class hierarchy per library instance, so
two copies of ``librogue-core`` mean the base class your module inherits from is
not the one Python already knows about.

This is easy to hit when a source-tree build and a packaged install coexist. Find
out how many you have:

.. code-block:: bash

   find / -name 'librogue-core.so*' 2>/dev/null

Then make sure ``CMAKE_PREFIX_PATH`` at build time, ``LD_LIBRARY_PATH`` at run
time, and the ``rogue`` package Python actually imports all refer to the same
installation.

**"No rule to make target .../lib/librogue-core.so"**

.. code-block:: text

   make: *** No rule to make target '<path>/lib/librogue-core.so.v6.15',
   needed by 'BitInverter.so'.  Stop.

``RogueConfig.cmake`` records an absolute library path assuming an installed
layout, with the library under ``lib/``. A plain in-place source build leaves it
in the build directory instead, so that path does not exist. Point
``CMAKE_PREFIX_PATH`` at a proper installation — a conda environment, or the
result of ``make install`` — rather than at a raw build tree.

When To Reach For C++
=====================

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Situation
     - Recommendation
   * - Prototyping any stream stage
     - Start in Python; it is far quicker to iterate
   * - Python stage measurably limiting throughput
     - Port that one stage to C++
   * - Per-frame work on a high-rate path
     - C++ from the outset
   * - Orchestration, configuration, tree logic
     - Keep it in Python regardless of rate

Measure before porting. A Python ``Slave`` handles modest frame rates without
difficulty, and a C++ module you did not need is a maintenance cost with no
return.

Where To Go Next
================

* :doc:`/custom_module/index` — the reference treatment of this workflow.
* :doc:`/custom_module/sourcefile` — the annotated C++ source.
* :doc:`/custom_module/makefile` — build configuration in detail.
* :doc:`/custom_module/rogueconfig` — the variables ``find_package(Rogue)``
  exports.
* :doc:`/custom_module/testing` — testing custom modules.
* :doc:`/api/cpp/index` — the C++ API reference.
