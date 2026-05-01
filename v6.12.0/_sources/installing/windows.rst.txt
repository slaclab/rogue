.. _installing_windows:

============================
Setting Up Ubuntu On Windows
============================

Running Rogue on Windows starts with setting up Ubuntu under WSL2. Rogue
itself is not installed natively on Windows; the supported path is to run it
inside the Linux environment provided by WSL2.

These instructions are valid for Windows 11 with WSL2.

For detailed installation instructions, refer to the official Microsoft WSL
documentation:

https://learn.microsoft.com/en-us/windows/wsl/install

WSL2 Graphics Support
=====================

Windows 11 includes WSLg (Windows Subsystem for Linux GUI), which provides
native support for running graphical Linux applications.
No additional X server installation is required.

Install Ubuntu On Windows
=========================

Open the Microsoft Store from the main menu. Search for ``Ubuntu``, select a
current LTS release such as Ubuntu 24.04 LTS, and install it.

Once installation is complete, Ubuntu appears in the main menu. Launch it to
open a Bash shell in the new Linux environment.

Verify WSL2
-----------

To verify you are running WSL2, open a Windows PowerShell or Command Prompt
window as administrator and run:

.. code::

   > wsl --list --verbose

Ensure your Ubuntu distribution shows version 2. If it shows version 1, upgrade
it with:

.. code::

   > wsl --set-version Ubuntu 2

You can now install and run Miniforge as described in
:ref:`installing_miniforge`. Graphical applications display through WSLg
without additional X server configuration.
