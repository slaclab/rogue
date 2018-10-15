# rogue
SLAC Python Based Hardware Abstraction &amp; Data Acquisition System

Email List For Announcements:
https://listserv.slac.stanford.edu/cgi-bin/wa?A0=AIR-ROGUE-USERS

JIRA:
https://jira.slac.stanford.edu/plugins/servlet/project-config/ESROGUE

Introduction presentation: 
https://docs.google.com/presentation/d/1m2nqGzCZXsQV8ul4d0Gk7xmwn-OLW1iucTLm7LLp9eg/edit?usp=sharing
some concepts (Blocks and Variables) are a little out of data as we have made changes.

For example scripts and sub-class source code examples see:

https://github.com/slaclab/rogue-example

## Getting Rogue Using Anaconda

Download and install miniconda if you don't already have it installed on your machine. Choose an install location with a lot of available diskspace. Anaconda appears to only work reliably in the bash shell. 

````
# wget https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh
# bash Anaconda3-5.3.0-Linux-x86_64.sh
````

You can setup anaconda with the following command:

````
$ source /path/to/my/anaconda3/etc/profile.d/conda.sh
````

Create and activate a rouge environment:

````
$ conda create -n rogue_env -c slacrherbst -c defaults -c conda-forge -c paulscherrerinstitute python=3.6 rogue
$ conda activate rogue_env
````

## Building & Installing Rogue
Before building and using rogue you will need to either install the required support packages 
and modules or setup an anaconda environment. See sections below for instructions.

There are three possible modes for building/installing rogue:

- Local:
   Rogue is going to be used in the local checkout directory. A setup script is generated to add rogue to the system environment.

- Custom:
   Rogue is going to be installed in a custom non-system directory. A setup script is generated to add rogue to the system environment.

- System:
   The rogue headers and libraries will be installed to a standard system directory and the python filed will be installed using the system python package installed.

### Local Install

````
$ git clone https://github.com/slaclab/rogue.git
$ cd rogue
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=local
$ make install
$ source ../setup_rogue.csh (or .sh)
````

### Custom Install

````
$ git clone https://github.com/slaclab/rogue.git
$ cd rogue
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=custom -DROGUE_DIR=/path/to/custom/dir
$ make install
$ source /path/to/custom/dir/setup_rogue.csh (or .sh)
````

### System Install

````
$ git clone https://github.com/slaclab/rogue.git
$ cd rogue
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=system
$ make install
````

### Updating rogue

to update from git and rebuild:
````
$ git pull
$ cd build
$ make rebuild_cache
$ make clean
$ make install
````

## Installing Packages Required For Rogue
See section below to use anaconda to manage the environment.

The following packages are required to build the rogue library:

- cmake   >= 3.5
- Boost   >= 1.58
- python3 >= 3.6
- bz2

To add these packages on Ubuntu 17.04 (or later):

````
$ apt-get install cmake (or cmake3)
$ apt-get install python3
$ apt-get install libboost-all-dev
$ apt-get install libbz2-dev
$ apt-get install python3-pip
$ apt-get install git
$ apt-get install libzmq3-dev
$ apt-get install python3-pyqt5 (or python3-pyqt4)
````

To add these packages on archlinux:

````
$ pacman -S cmake
$ pacman -S python3
$ pacman -S boost
$ pacman -S bzip2
$ pacman -S python-pip
$ pacman -S git
$ pacman -S zeromq
$ pacman -S python-pyqt5 (or python-pyqt4)
````

Epics V3 support is and optional module that will be included in the rogue build
if the EPICS_BASE directory is set in the user's environment.

### Python packages required

The following python packages are required to use rogue in the python3
environment. Currently I am using PIP to install these, but you are free 
to use your favorite python tool.

````
$ pip3 install PyYAML
$ pip3 install Pyro4 
$ pip3 install parse
$ pip3 install click
$ pip3 install pyzmq
$ pip3 install mysqlclient
````

## Building Inside An Anaconda Environment

Download and install miniconda if you don't already have it installed on your machine. Choose an install location with a lot of available diskspace. Anaconda appears to only work reliably in the bash shell. 

````
# wget https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh
# bash Anaconda3-5.3.0-Linux-x86_64.sh
````

You can setup anaconda with the following command:

````
$ source /path/to/my/anaconda3/etc/profile.d/conda.sh
````

Create the rogue environment (required once):

````
$ cd rogue
$ conda env create -n rogue_env -f rogue_conda.yml
````

Activate the rogue environment

````
$ conda activate rogue_env 
````

You can then build the project using the instructions above.

## Installing Rogue and Anaconda behind a proxy

To install rogue and anaconda behind a firewall you will need an ssl capable https proxy. I have used mitmproxy with success:

````
$ mitmproxy --list-host=gateway.machine.com --list-port=8080
````

You will execute a number of steps to enable proxy for wget, git and anaconda

````
$ setenv https_proxy gateway.machine.com:8080
$ git config --global https.proxy https://gateway.machine.com:8080
$ git config --global http.sslVerify false
````

Create a file $HOME/.condarc and add the following lines:

````
proxy_servers:
   http:http://gateway.machine.com:8080
   https:https://gateway.machine.com:8080

ssl_verify: false
````

