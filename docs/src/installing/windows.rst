.. _installing_windows:

============================
Setting Up Ubuntu On Windows
============================

The following instructions setup an *Ubuntu On Windows* environment required for running Rogue in Miniforge (or build from source) in Windows.
These instructions are valid for Windows 11 with WSL2.

For detailed installation instructions, refer to the official Microsoft WSL documentation:

https://learn.microsoft.com/en-us/windows/wsl/install

WSL2 Graphics Support
=====================

Windows 11 includes WSLg (Windows Subsystem for Linux GUI), which provides native support for running graphical Linux applications. 
No additional X server installation is required.

Install Ubuntu On Windows
==========================

Open up the *Microsoft Store* icon from the main menu. In the search box
enter the text *Ubuntu*. Select the *Ubuntu* icon (latest LTS version such as Ubuntu 24.04 LTS) 
and install the package.

Once installation is complete you can find Ubuntu on the main menu as *Ubuntu*. A bash text
window will open with an Ubuntu bash prompt.

Verify WSL2
-----------

To verify you are running WSL2, open a Windows PowerShell or Command Prompt window and run as adminstrator:

.. code::

   > wsl --list --verbose

Ensure your Ubuntu distribution shows version 2. If it shows version 1, upgrade it with:

.. code::

   > wsl --set-version Ubuntu 2

You are now able to install and run miniforge as described in :ref:`installing_miniforge`. 
Graphical applications will automatically display using WSLg without additional configuration.
