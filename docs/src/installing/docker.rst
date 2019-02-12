.. _installing_docker:

=======================
Installing Rogue Docker
=======================

Docker images with rogue are automatically generated and uploaded to Docker hub, in the following repositories:

Docker images with tagged (stable) version of rogue:
https://hub.docker.com/r/tidair/rogue/

Docker images with development versions of rogue:
https://hub.docker.com/r/tidair/rogue-dev/

The images can be used to run rogue applications as one would normally do using a local installation of rogue.

How To Get The Container
========================

To get the most recent version of the docker image, first you will need to install docker in you host OS and be logged in. Then you can get a copy by running:

.. code::

   $ docker pull tidair/rogue

to get the latest version available, or:

.. code::

   $ docker pull tidair/rogue:$TAG

to get a specific tagged version.

**Notes:**

* The docker images are tagged using the same rogue tag.
* You can also pull development version using `tidair/rogue-dev` instead.

How To Run The Container
========================

To run a rogue application inside a container, you must first have a copy of the application in in your host OS. Also, your host must have a direct connection to your target FPGA.

Then you can run the container, for example, like this:

.. code::

   $ docker run -ti -v <APP_DIR>:/python tidair/rogue /python/<APP_NAME>

where:

* **APP_DIR** is the full path to the folder containing your application,
* **APP_NAME** is the name of your application script.

If your application uses a graphical interface, then you need to pass additional arguments in order to properly forward X:

On A Linux OS
=============

.. code::

   $ docker run -ti \
      -u $(id -u) \
      -e DISPLAY=unix$DISPLAY \
      -v "/tmp/.X11-unix:/tmp/.X11-unix" \
      -v "/etc/group:/etc/group:ro" \
      -v "/etc/passwd:/etc/passwd:ro" \
      -v <APP_DIR>:/python \
      tidair/rogue /python/<APP_NAME>

On A MAX OS
===========

First install XQuartz. Then run it from the command line using `open -a XQuartz`. In the XQuartz preferences, go to the “Security” tab and make sure you’ve got “Allow connections from network clients” ticked.

Now run:

.. code::

   $ IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
   $ xhost + $IP
   $ docker run -ti -e DISPLAY=$IP:0 -v <APP_DIR>:/python tidair/rogue /python/<APP_NAME>

**Notes:**

* The `-v` option maps a folder in your host OS inside the docker container. In this example we are mapping our local folder containing the rogue application to `/python/` inside the container. Then, when the container runs, we are able to access the rogue application which is now located at `/python/`. You can, of course, map more than one folder inside the container, as well as using different locations inside the container.
* You can also run a specific tagged version of rogue changing `tidair/rogue` for `tidair/rogue:<TAG>` in the docker run command. Moreover, you can run development version using `tidair/rogue-dev` (latest version) or `tidair/rogue-dev:<TAG>` (a specific version).

How To Build A Custom Docker Image With Rogue
=============================================

You can create custom docker image, using the Docker image containing rogue as a starting point. Just start your `Dockerfile` with this line:

.. code::

   FROM tidair/rogue:<TAG>

