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
foundational ``Device`` transaction model built around write, verify, read,
and check. Variable APIs present the value-oriented surface, while ``Device``
owns the bulk traversal and transaction model underneath.

What You Usually Set
====================

The generated API reference contains the full constructor signature for each
Variable class. The narrative docs have a narrower job: explain the shared
parameters that most often shape how a Variable behaves in a tree. The subtype
pages then add the parameters that matter most for their own behavior, such as
``offset`` for ``RemoteVariable`` or ``dependencies`` for ``LinkVariable``.

Across the Variable types, these are the parameters that usually deserve the
most attention:

.. list-table::
   :widths: 22 78
   :header-rows: 1

   * - Parameter
     - Role
   * - ``name``
     - Defines the tree path segment and the attribute name users interact
       with.
   * - ``description``
     - Provides short operator-facing help text for GUIs, scripts, and other
       tooling.
   * - ``mode``
     - Controls read and write policy, usually ``RW``, ``RO``, or ``WO``.
   * - ``disp``
     - Formats values for display-oriented APIs such as ``getDisp()``.
   * - ``enum``
     - Maps integer values to named states.
   * - ``units``
     - Labels the engineering meaning of the value.
   * - ``pollInterval``
     - Enables periodic refresh for changing status or telemetry.
   * - ``hidden``
     - Removes the Variable from normal user-facing views when set to
       ``True``.
   * - ``groups``
     - Adds labels that tree-level tools and workflows can use for filtering
       or policy decisions.

Start by getting ``name`` and ``description`` right. Those two fields do most
of the work of making a tree understandable to users, GUIs, and scripts, and
they usually matter more than lower-priority metadata.

Use ``mode`` to express intent clearly. ``RW`` fits normal configuration and
readable state, ``RO`` fits telemetry, status, counters, and derived views,
and ``WO`` fits strobes, triggers, and other write-only control surfaces.

Use ``disp``, ``enum``, and ``units`` to make the value readable in operator
terms instead of exposing only the raw stored representation. That is often
the difference between a tree that feels like a register map and one that
feels like an interface.

Use ``pollInterval`` selectively for changing status and telemetry. Values
that rarely change usually read better as on-demand state than as constant
background traffic. For the scheduling model behind polling, see
:doc:`/pyrogue_tree/core/poll_queue`.

Use ``hidden`` and ``groups`` to control how the Variable participates in
presentation and higher-level workflows. ``hidden=True`` removes it from
normal user-facing views, while ``groups`` provides labels for filtering and
policy decisions. For the grouping model itself, see
:doc:`/pyrogue_tree/core/groups`.

Choosing The Right Variable Type
================================

PyRogue provides three primary Variable subtypes:

.. toctree::
   :maxdepth: 1
   :hidden:

   local_variable
   remote_variable
   link_variable

Choose:

* :doc:`/pyrogue_tree/core/local_variable` when the value is owned by Python
  logic rather than by hardware registers.
* :doc:`/pyrogue_tree/core/remote_variable` when the value maps into hardware
  memory or register space.
* :doc:`/pyrogue_tree/core/link_variable` when you want a derived view built
  from one or more other Variables.

That is also the conceptual progression most users need: software-owned
state first, then register-backed state, then derived operator-facing views
built on top of the others.

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

Value Presentation And Value Storage
====================================

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
``get()``, ``set()``, and for hardware-backed cases, sometimes ``post()``.

At a conceptual level:

* ``get()`` returns a Variable value in its native Python type
* ``set()`` accepts a native Python value and updates the Variable
* ``post()`` issues a posted (non-blocking) write for hardware-backed Variables

For hardware-backed Variables, those calls may also initiate bus activity.
For software-backed or linked Variables, ``get()`` and ``set()`` call into the
subtype's local or linked behavior instead.

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

``post(value)`` is narrower than the core ``Device`` block operations. It is a
per-Variable hardware API that issues a posted write directly through the
backing ``Block`` rather than through the normal ``parent.writeBlocks()`` path.
That makes it useful for self-clearing command bits, trigger registers, and
``RemoteCommand`` helpers whose intended hardware interaction is specifically a
posted write.

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
