.. _starting_tutorials:

==================================
PyRogue Tree Getting Started Guide
==================================

This guide provides a quick walkthrough of a basic PyRogue tree application.
It walks from a minimal root setup through custom device definition, then
finishes with complete reference code.

Recommended learning path
=========================

#. :ref:`introduction` - review the Rogue architecture and concepts.
#. :ref:`tutorials_p_t_root` - build a minimal working root and add common
   components.
#. :ref:`tutorials_p_t_device` - define a custom `pyrogue.Device` with
   `RemoteVariable`, `LinkVariable`, and `RemoteCommand` entries.
#. :ref:`full_root_definition` - review the full assembled example in one place.


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
