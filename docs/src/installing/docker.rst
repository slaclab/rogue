.. _installing_docker:

===========================
Running Rogue With Docker
===========================

Rogue container images are published to GitHub Container Registry (GHCR). This
path is useful when:

- You want a reproducible runtime environment without managing local
  dependencies,
- You are running on a platform where native installation is inconvenient,
- Or you want to package an application on top of a known Rogue base image.

Tagged images are published at:

https://ghcr.io/slaclab/rogue

They can be used to run Rogue applications much like a local installation,
provided the container still has access to the required hardware and any GUI
forwarding path you need.

How To Get The Container
========================

To get the most recent released Rogue container, first install Docker on the
host system and ensure you are logged in. Then pull the image:

.. code::

   $ docker pull ghcr.io/slaclab/rogue:latest

Or target a specific tagged version:

.. code::

   $ docker pull ghcr.io/slaclab/rogue:$TAG


**Notes:**

* The Docker images use the same release tags as Rogue itself.

How To Run The Container
========================

To run a Rogue application inside a container, you must already have a copy of
the application on the host system. The host must also retain the required
connection to the target FPGA or other hardware.

Then you can run the container, for example, like this:

.. code::

   $ docker run -ti -v <APP_DIR>:/python ghcr.io/slaclab/rogue /python/<APP_NAME>

where:

* **APP_DIR** is the full path to the folder containing your application,
* **APP_NAME** is the name of your application script.

If your application uses a graphical interface, pass the additional arguments
required for X11 forwarding.

As a quick check, you can test the Docker installation and X11 forwarding with:

.. code::

   $ setfacl -m user:0:r ${HOME}/.Xauthority
   $ docker run -ti --net=host -e DISPLAY -v ${HOME}/.Xauthority:/root/.Xauthority ghcr.io/slaclab/rogue python3 -m pyrogue.examples --gui

GUI On A Linux OS
=================

.. code::

   $ docker run -ti \
      -u $(id -u) \
      -e DISPLAY=unix$DISPLAY \
      -v "/tmp/.X11-unix:/tmp/.X11-unix" \
      -v "/etc/group:/etc/group:ro" \
      -v "/etc/passwd:/etc/passwd:ro" \
      -v <APP_DIR>:/python \
      ghcr.io/slaclab/rogue /python/<APP_NAME>

GUI On A macOS Host
===================

First install XQuartz. Then start it with ``open -a XQuartz``. In the XQuartz
preferences, under the Security tab, ensure that
``Allow connections from network clients`` is enabled.

Now run:

.. code::

   $ IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
   $ xhost + $IP
   $ docker run -ti -e DISPLAY=$IP:0 -v <APP_DIR>:/python ghcr.io/slaclab/rogue /python/<APP_NAME>

**Notes:**

- The ``-v`` option maps a host directory into the container. In the examples
  above, the host application directory is mapped to ``/python`` inside the
  container.
- You can also run a specific tagged version by replacing
  ``ghcr.io/slaclab/rogue`` with ``ghcr.io/slaclab/rogue:<TAG>``.

How To Build A Custom Docker Image With Rogue
=============================================

You can create a custom Docker image by using the Rogue image as a base. Start
your ``Dockerfile`` with:

.. code::

   FROM ghcr.io/slaclab/rogue:<TAG>
