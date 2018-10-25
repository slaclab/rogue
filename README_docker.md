# Docker Image with Rogue

Docker images with Rogue are automatically generated and uploaded to Docekr hub, in the following repositories:

- Docker images with tagged (stable) version of Rogue:
https://hub.docker.com/r/tidair/rogue/

- Docker images with development versions of Rogue:
https://hub.docker.com/r/tidair/rogue-dev/

The images can be used to run Rogue applications as one would normally do using a local installation of Rogue.

## How to get the container

To get the most recent version of the docker container, first you will need to install docker in you host OS and be logged in. Then you can get a copy of this docker container by running:

```
docker pull tidair/rogue
```

to get the latest version availbale, or:

```
docker pull tidair/rogue:$TAG
```
to get an specific tagged version.

**Notes:**
- The docker images are tagged usging the same Rogue tag.
- You can also pull development version using `tidair/rogue-dev` instead.

## How to run the container

To run a Rogue application inside a container, you must first have a copy of the application in in your host. Also, your host must have a direct connection to your target FPGA.

Then you can run the container, for example, like this:

```
$ docker run -ti \
-v <APP_DIR>:/python \
tidair/rogue \
/python/<APP_NAME>
```

where:
- **APP_DIR** is the full path you the folder containing you application,
- **APP_NAME** is the name of your application script.

If you application uses a graphical interface, then you need to pass additional argument to docker in order to properly forward X:

### On a Linux OS:

```
$ docker run -ti \
-u $(id -u) \
-e DISPLAY=unix$DISPLAY \
-v "/tmp/.X11-unix:/tmp/.X11-unix" \
-v "/etc/group:/etc/group:ro" \
-v "/etc/passwd:/etc/passwd:ro" \
-v <APP_DIR>:/python \
tidair/rogue \
/python/<APP_NAME>
```

### On a MAX OS:

First install XQuartz. Then run it from the command line using `open -a XQuartz`. In the XQuartz preferences, go to the “Security” tab and make sure you’ve got “Allow connections from network clients” ticked.

Now run:

```
$ IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
$ xhost + $IP
$ docker run -ti \
-e DISPLAY=$IP:0 \
-v <APP_DIR>:/python \
tidair/rogue \
/python/<APP_NAME>
```

Notes:
- The `-v` option maps a folder in your host OS inside the docker container. In this example we are mapping our local folder containing the Rogue application application in `/python/` inside the docker. Then, when the docker runs, we are able to access the Rogue application which is now located at `/python`. You can, of course, map more than one folder inside the container, and can use different locations inside the container.
- You can also run a specific tagged version of rogue charing `tidair/rogue` for `tidair/rogue:<TAG>` in the docker run command. Moreover, you can run development version using `tidair/rogue-dev` (lastest version) or `tidair/rogue-dev:<TAG>` (an espedific version).

## How to build a custom docker image with Rogue

You can create custom docker image, using the Docker image containing Rogue as a starting point. Just start your `Dockerfile` with:

```
FROM tidair/rogue:<TAG>
```
