.. _installing_windows:

============================
Setting Up Ubuntu On Windows
============================

The following instructions setup an *Ubuntu On Windows* environment required for running Rogue in Anaconda in Windows. These
instructions are valid for Windows 10 and above.

Install XMING
=============

XMing is required for using the Rogue graphical interface in the Windows environment.

https://sourceforge.net/projects/xming/

Install Ubuntu On Windows
=========================

Open up the *Microsoft Store* icon from the main menu. In the search box
enter the text *Ubuntu*. Select the *Ubuntu 18.04* icon (or higher version
when available) and install the package.

Once installation is complete you can find Ubuntu on the main menu as *Ubuntu 18.04*. A bash text
window will open with an Ubuntu bash prompt.

After first installation you will want to run the following command to setup 
the display environment.

.. code::

   $ echo "export DISPLAY=:0" >> ~/.bashrc

You are now able install and run anaconda as described in :ref:`installing_anaconda`.

