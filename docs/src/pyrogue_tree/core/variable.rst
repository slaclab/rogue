.. _pyrogue_tree_node_variable:

========
Variable
========

Variables are the value-carrying Nodes in the PyRogue tree. They are the main
way a tree exposes state to users, GUIs, scripts, and higher-level software.
In practice, most of what operators read and most of what applications
configure flows through ``Variable`` Nodes.

A Variable can represent:

* Software-owned state.
* A hardware register or bit field.
* A derived engineering view computed from other Variables.

That breadth is why Variable design matters so much to the quality of a tree.
Good Variables make the system readable, scriptable, and safe to operate.

What Variables Provide
======================

Across the different subtypes, Variables provide a shared set of behaviors:

* Typed values and display formatting.
* Access-mode control such as ``RW``, ``RO``, and ``WO``.
* Units, enums, limits, and display metadata.
* Update notifications for GUIs and remote listeners.
* Optional polling and hardware-backed access behavior.

Those common behaviors are what make local, remote, and linked Variables feel
like one coherent part of the tree, even though their implementations differ.

For hardware-backed Variables, the actual bus activity still flows through the
foundational ``Device`` operations: write, verify, read, and check. In other
words, Variable APIs present the value-oriented surface, while ``Device`` owns
the bulk transaction model underneath.

Choosing The Right Variable Type
================================

PyRogue provides three primary Variable subtypes:

.. toctree::
   :maxdepth: 1
   :caption: Variable Types:

   local_variable
   remote_variable
   link_variable

In practice, the choice is usually straightforward:

* :py:class:`~pyrogue.LocalVariable` for values owned by Python logic rather
  than by hardware registers.
* :py:class:`~pyrogue.RemoteVariable` for values mapped into hardware memory or
  register space.
* :py:class:`~pyrogue.LinkVariable` for derived values built from one or more
  other Variables.

That progression is also the conceptual progression most users need:
``LocalVariable`` explains software-owned state, ``RemoteVariable`` explains
register-backed state, and ``LinkVariable`` explains how to present a more
useful derived view on top of the others.

Common Design Questions
=======================

When defining a Variable, the important questions are usually:

* Who owns the value: software, hardware, or another Variable?
* Should users see the raw value, a converted value, or both?
* Is the value read-only, write-only, or read-write?
* Should it participate in polling or only update on demand?
* Does the displayed form need units, enums, or custom formatting?

Those questions affect not only the Variable subtype, but also how clear the
tree will be to remote tools such as PyDM and command-line clients.

Polling And Update Behavior
===========================

Variables with non-zero ``pollInterval`` participate in the Root-owned polling
workflow. That is most often relevant for hardware-backed status and telemetry
values that change over time.

In general:

* Poll values that operators or software genuinely need to monitor.
* Avoid turning rarely used configuration registers into continuously polled
  traffic.
* Use derived Variables carefully when their dependencies are polled, so the
  resulting update behavior stays understandable.

For the scheduling model itself, see :doc:`/pyrogue_tree/core/poll_queue`.

Variable Presentation Vs Variable Storage
=========================================

One of the most useful ways to think about Variables is to separate what users
see from how values are stored.

Examples:

* A ``RemoteVariable`` may store a raw register value while presenting units,
  limits, and formatting metadata.
* A ``LinkVariable`` may expose engineering units while leaving the raw
  register access available through one or more underlying Variables.
* A ``LocalVariable`` may present a live view of Python-owned state without any
  hardware transaction path at all.

This is one of the core reasons PyRogue trees work well for both hardware
developers and operators: the same system can preserve raw control surfaces and
also expose safer, more meaningful user-facing values.

Core Access Methods
===================

Across the Variable subtypes, the most important day-to-day APIs are
``get()`` and ``set()``.

At a conceptual level:

* ``get()`` returns a Variable value in its native Python type
* ``set()`` accepts a native Python value and updates the Variable

For hardware-backed Variables, those calls may also initiate bus activity.
For software-backed or linked Variables, they call into the subtype's local or
linked behavior instead.

The most important control flags are:

* ``read`` on ``get()``
* ``write`` on ``set()``

Using ``get(read=True)`` means "refresh from the underlying source before
returning the value." For a ``RemoteVariable``, that usually means issuing a
hardware read. Using ``get(read=False)`` means "return the currently cached
value without forcing a new transaction."

Using ``set(write=True)`` means "apply the new value and push it through the
normal write path." Using ``set(write=False)`` means "update or stage the value
without immediately committing it." That distinction matters in bulk
configuration flows, linked conversions, and any code that wants to stage
several dependent updates before writing them together.

Those same ideas propagate into ``LinkVariable`` callbacks. A good
``linkedGet`` should normally respect the caller's ``read`` choice, and a good
``linkedSet`` should normally respect the caller's ``write`` choice.

Display-Oriented Access
=======================

PyRogue also exposes display-form accessors alongside the native-value access
methods:

* ``getDisp()`` performs ``get()`` and returns the display-formatted string
* ``setDisp()`` parses a display-formatted string and then calls ``set()``

The display form is built from the Variable's ``disp`` setting.

In the common case, ``disp`` is a Python format string such as:

* ``'{:d}'`` for decimal integers
* ``'{:#x}'`` for hexadecimal integers
* ``'{:.3f}'`` for fixed-point floating-point display

When ``getDisp()`` or ``valueDisp()`` is called, PyRogue formats the current
native value through that ``disp`` string. When ``setDisp()`` is called,
PyRogue parses the display-form input back into the native value type and then
calls ``set()``.

Two special cases are also common:

* Enum-backed Variables can use display mappings so the user sees names rather
  than raw numeric values.
* Array-valued Variables format each element using the same display rule.

These methods are useful when the interaction is text-oriented rather than
type-oriented, for example:

* Command-line tools
* GUI widgets
* YAML and other serialized configuration flows
* Enum-backed or formatted values where the display form matters

Cached Value Shortcuts
======================

Two related convenience methods expose the cached value without forcing a new
read:

* ``value()`` is equivalent to ``get(read=False)``
* ``valueDisp()`` is equivalent to ``getDisp(read=False)``

These are useful when the caller wants the current tree state as it already
exists locally, without implying that the underlying source should be accessed
again.

Advanced Related Topics
=======================

Some Variable mechanics are important, but they read better as separate pages:

* :doc:`/pyrogue_tree/core/block` for how hardware-backed Variables are grouped
  into transaction units.
* :doc:`/pyrogue_tree/core/model` for how typed byte conversion works.
* :doc:`/pyrogue_tree/core/memory_variable_stream` for bridging Variable
  updates into stream-processing paths.

Those are all part of the Variable story, but they are advanced enough that
they should not interrupt the basic explanation of what a Variable is and when
to use each subtype.

What To Explore Next
====================

* Software-owned values: :doc:`/pyrogue_tree/core/local_variable`
* Register-backed values: :doc:`/pyrogue_tree/core/remote_variable`
* Derived values and engineering views: :doc:`/pyrogue_tree/core/link_variable`
* Typed conversion rules: :doc:`/pyrogue_tree/core/model`
* Block transaction behavior: :doc:`/pyrogue_tree/core/block`

API Reference
=============

See :doc:`/api/python/pyrogue/basevariable` for generated API details.
