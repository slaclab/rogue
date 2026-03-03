.. _starting_tutorials:

==================================
PyRogue Tree Getting Started Guide
==================================

This guide is the fastest way to build and understand a basic PyRogue tree.
It walks from a minimal root setup through custom device definition, then
finishes with complete reference code.

If you have not already reviewed Rogue architecture, start with
:ref:`introduction` first.

Recommended learning path
=========================

#. :ref:`tutorials_p_t_root` - build a minimal working root and add common
   components.
#. :ref:`tutorials_p_t_device` - define a custom `pyrogue.Device` with
   `RemoteVariable`, `LinkVariable`, and `RemoteCommand` entries.
#. :ref:`full_root_definition` - review the full assembled example in one place.

Optional extensions
===================

After completing the core flow, see
:ref:`interfaces_python_osmemmaster` for a memory-backed monitoring extension.

External hardware-oriented walkthrough
======================================

For a board-focused example using Rogue with hardware:

* Tutorial page: `Simple-PGPv4-KCU105 Example <https://slaclab.github.io/Simple-PGPv4-KCU105-Example/>`_
* Source repository: `slaclab/Simple-PGPv4-KCU105-Example <https://github.com/slaclab/Simple-PGPv4-KCU105-Example>`_

.. toctree::
   :maxdepth: 1
   :caption: Getting Started Pages:

   pyrogue_tree_example/p_t_root
   pyrogue_tree_example/p_t_device
   pyrogue_tree_example/full_root
