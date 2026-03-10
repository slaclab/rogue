.. _migration:

===============
Migration Notes
===============

This section collects version-to-version upgrade notes for Rogue and PyRogue.
Use it when an existing application or Device library needs to move forward
across a release boundary and you want to identify behavioral changes, removed
APIs, and the newer patterns that replace them.

Migration notes are intentionally narrower than the main narrative
documentation. The rest of the manual explains how the current APIs and
workflows are intended to be used. This section focuses on what changed and
what older code needs to be updated.

In practice, a migration pass usually involves:

1. Identifying features that moved to a different subsystem or interface model,
2. Updating construction and lifecycle patterns,
3. Replacing removed APIs with the supported equivalents,
4. Then returning to the main section docs for the current recommended design.

Not every release needs a migration note. These pages are only added when a
version introduces changes that are significant enough to affect existing
applications.

What To Explore In This Section
===============================

- :doc:`rogue_v6` for the major interface and API transitions introduced in
  Rogue V6

What To Explore Next
====================

- Current PyRogue tree model and lifecycle behavior: :doc:`/pyrogue_tree/index`
- Built-in interface and protocol documentation: :doc:`/built_in_modules/index`
- API reference for exact class and method details: :doc:`/api/index`

.. toctree::
   :maxdepth: 1
   :caption: Migration:

   rogue_v6
