
A recent version of autoconf is required for some of the packages needed
by rogue. At SLAC a proper version can be found at: 

> source /afs/slac.stanford.edu/g/reseng/vol11/autoconf/2.69/settings.csh
or
# source /afs/slac.stanford.edu/g/reseng/vol11/autoconf/2.69/settings.sh

You need to either use the the above version or download it and compile 
it on your own. Most modern versions of linux have the appropriate version.

For archlinux on the RCE:
> pacman -S autoconf automake pkg-config git

