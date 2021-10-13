.. _channel_urls

============
Channel URLS
============

When using the PyDM and Rogue widgets the user must associate the widget with a Rogue Device, Variable or Command using a channel URL. The URLs used by Rogue connected widgets are in the form:

rogue://0/MyRoot.MyDevice.MyVariable

The user can either use the real root name or simply the 'root' alias when referring to a Rogue root instance. This is usefull when creating generic debug tree associations. For example the URL used by a generic DebugTree widdget would be:

rogue://0/root

URL Suffix
==========

For some channels such as variables and commands a suffix can be added to the URL to direct PyDM on how to access the Rogue instance. An example suffix usage is:

rogue://0/root.Device.Variable/disp

The following suffixes are currently supported:

   - name: The PyDM widget will display the Rogue instance name instead of its value. This is usefull for labels.
   - path: The PyDM widget will display the full Rogue path of the instance.
   - disp: The PyDM widget will use the getDisp() call instead of get() to display the string representation of the current value. This is usefull for line edit widgets.

