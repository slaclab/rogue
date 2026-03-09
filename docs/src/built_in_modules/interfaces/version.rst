.. _interfaces_version:

====================
Rogue Version Helper
====================

Rogue provides version/query helpers through ``rogue::Version`` in C++ and
``rogue.Version`` in Python.

The helper is useful for:

* Logging the currently installed Rogue version
* Enforcing minimum/maximum/exact version requirements
* Retrieving parsed version components (major/minor/maint/devel)

Notes
-----

* ``current()`` returns the compiled Rogue version string (typically prefixed
  with ``v``, for example ``v6.3.0-0-g<hash>``).
* Comparison helpers (``greaterThanEqual``, ``minVersion``, etc.) expect
  version strings in ``major.minor.maint`` form (for example ``"6.3.0"``).
* ``pythonVersion()`` returns a Python-style version string (for example
  ``"6.3.0"`` or ``"6.3.0.dev4"``).

Python examples
---------------

.. code-block:: python

   import rogue

   # Report installed Rogue build and parsed components.
   print("Rogue current:", rogue.Version.current())
   print("Rogue pythonVersion:", rogue.Version.pythonVersion())
   print("major/minor/maint/devel:",
         rogue.Version.major(),
         rogue.Version.minor(),
         rogue.Version.maint(),
         rogue.Version.devel())

   # Boolean check without raising.
   if not rogue.Version.greaterThanEqual("6.0.0"):
       raise RuntimeError("Rogue >= 6.0.0 is required")

   # Hard guard: raises if the requirement is not met.
   rogue.Version.minVersion("6.0.0")

.. code-block:: python

   import rogue

   try:
       # Hard guard for exact deployed version.
       rogue.Version.exactVersion("6.3.0")
       print("Exact version match")
   except Exception as exc:
       print(f"Version mismatch: {exc}")


C++ examples
------------

.. code-block:: cpp

   #include "rogue/Version.h"
   #include <iostream>

   int main() {
       // Report installed Rogue build and parsed components.
       std::cout << "Rogue current: " << rogue::Version::current() << "\n";
       std::cout << "major.minor.maint: "
                 << rogue::Version::getMajor() << "."
                 << rogue::Version::getMinor() << "."
                 << rogue::Version::getMaint() << "\n";

       // Boolean check without throwing.
       if (!rogue::Version::greaterThanEqual("6.0.0")) {
           std::cerr << "Rogue >= 6.0.0 is required\n";
           return 1;
       }

       // Throws rogue::GeneralError if requirement is not met.
       rogue::Version::minVersion("6.0.0");
       return 0;
   }

.. code-block:: cpp

   #include "rogue/Version.h"
   #include "rogue/GeneralError.h"
   #include <iostream>

   int main() {
       try {
           // Guard upper bound and exact requirement.
           rogue::Version::maxVersion("7.0.0");
           rogue::Version::exactVersion("6.3.0");
   } catch (const rogue::GeneralError& e) {
           std::cerr << "Version check failed: " << e.what() << "\n";
           return 1;
       }
       return 0;
   }

What To Explore Next
====================

- Built-in section overview: :doc:`/built_in_modules/index`
- Deployment and environment setup: :doc:`/installing/index`
