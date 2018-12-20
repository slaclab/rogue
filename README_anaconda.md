# Installing Rogue With Anaconda

This README provides instructions for installing a pre-built rogue package inside an anaconda environment.

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

## Creating A Rogue Environment

The next step is to create ana anaconda environment which includes the rogue package.

````
$ conda create -n rogue_env -c defaults -c conda-forge -c paulscherrerinstitute -c tidair-tag python=3.6 rogue
````

The order of the args is important. tidair-tag is the channel from which the rogue package is downloaded. Replace tidair-tag with tidair-dev to download the latest pre-release development version.

You now have an anaconda environment named rogue_env which contains all of the packages required to run rogue.

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

If you want to update rogue, run the following command after activating the rogue environment

````
$ conda update rogue -c tidair-tag
````

Replace tidair-tag with tidair-dev for pre-release

## Deleting Anaconda Environment

Run the following commands to delete the anaconda environment.

````
$ conda env remove -n rogue_env
````


