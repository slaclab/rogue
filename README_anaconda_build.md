# Building Rogue Inside Anaconda

This README provides instructions for downloading and building rogue inside an anaconda environment.
This currently only works for Linux-x64. Macos is not yet supported.

## Getting Anaconda

Download and install anaconda (or miniconda) if you don't already have it installed on your machine. Choose an install location with a lot of available diskspace (> 5GB). Anaconda appears to only work reliably in the bash shell. 

Go to https://www.anaconda.com/download to get the latest version of anaconda. Example steps for installing anaconda are included below:

````
# wget https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh
# bash Anaconda3-5.3.0-Linux-x86_64.sh
````

You do not need to install visual studio.

Use the following command to add anaconda to your environment. This can be added to your .bash_profile.

````
$ source /path/to/my/anaconda3/etc/profile.d/conda.sh
````

## Downloading Rogue & Creating Anaconda Envrionment

The next step is to download rogue and create a rogue compatable anaconda environment.

````
$ git clone https://github.com/slaclab/rogue.git
$ cd rogue
$ conda env create -n rogue_env -f rogue_conda.yml
````

You now have an anaconda environment named rogue_env which contains all of the packages required to build and run rogue.

To activate this environment:

````
$ conda activate rogue_env
````

## Building Rogue

Once the rogue environment is activated, you can build and install rogue

````
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=conda
$ make
$ make install
````

Rogue is now installed within the anaconda rogue environment. The download directory is no longer required and can be removed.

## Using Rogue

No additional setup scripts need to be run rogue in an anaconda environment. To activate and de-activate the rogue environment you can use the following commands:

To activate:

````
$ conda activate rogue_env
````

To deactivate:

````
$ conda deactivate
````

## Updating Rogue

If you want to update and re-install rogue, run the following commands.

````
$ cd rogue
$ rm -rf build
$ git pull
$ mkdir build
$ cd build
$ cmake .. -DROGUE_INSTALL=conda
$ make
$ make install
````

## Deleting Anaconda Environment

Run the following commands to delete the anaconda environment.

````
$ conda env remove -n rogue_env
````

