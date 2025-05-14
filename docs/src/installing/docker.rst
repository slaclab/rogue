.. _installing_docker:

=======================
Installing Rogue Docker
=======================

Docker images with rogue are automatically generated and uploaded to Docker hub, in the following repositories:

Docker images are created for tagged version of rogue:
https://ghcr.io/slaclab/rogue

The images can be used to run rogue applications as one would normally do using a local installation of rogue.

How To Get The Container
========================

To get the most recent released docker container of rogue, first you will need to install docker in you host OS and be logged in. Then you can get a copy by running:

.. code::

   $ docker pull ghcr.io/slaclab/rogue:latest

Or you can target a specific tagged version.

.. code::

   $ docker pull ghcr.io/slaclab/rogue:$TAG


**Notes:**

* The docker images are tagged using the same rogue tag.

How To Run The Container
========================

To run a rogue application inside a container, you must first have a copy of the application in in your host OS. Also, your host must have a direct connection to your target FPGA.

Then you can run the container, for example, like this:

.. code::

   $ docker run -ti -v <APP_DIR>:/python ghcr.io/slaclab/rogue /python/<APP_NAME>

where:

* **APP_DIR** is the full path to the folder containing your application,
* **APP_NAME** is the name of your application script.

If your application uses a graphical interface, then you need to pass additional arguments in order to properly forward X:

As an example use can test the docker install and X11 with the following command:

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

GUI On A MAX OS
===============

First install XQuartz. Then run it from the command line using `open -a XQuartz`. In the XQuartz preferences, go to the “Security” tab and make sure you’ve got “Allow connections from network clients” ticked.

Now run:

.. code::

   $ IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
   $ xhost + $IP
   $ docker run -ti -e DISPLAY=$IP:0 -v <APP_DIR>:/python ghcr.io/slaclab/rogue /python/<APP_NAME>

**Notes:**

* The `-v` option maps a folder in your host OS inside the docker container. In this example we are mapping our local folder containing the rogue application to `/python/` inside the container. Then, when the container runs, we are able to access the rogue application which is now located at `/python/`. You can, of course, map more than one folder inside the container, as well as using different locations inside the container.
* You can also run a specific tagged version of rogue changing `ghcr.io/slaclab/rogue` for `ghcr.io/slaclab/rogue:<TAG>` in the docker run command.

How To Build A Custom Docker Image With Rogue
=============================================

You can create custom docker image, using the Docker image containing rogue as a starting point. Just start your `Dockerfile` with this line:

.. code::

   FROM ghcr.io/slaclab/rogue:<TAG>

