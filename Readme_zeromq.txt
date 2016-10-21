Compiling zeromq

----------------------------------------------------------
Required Packages
----------------------------------------------------------
A recent version of autoconf is required, which is not 
available in rhel6. At SLAC a proper version can be found at: 

/afs/slac.stanford.edu/g/reseng/vol11/autoconf/autoconf-2.69

You need to either install autoconf, the the above version
or download it and compile it on your own. Most modern versions
of linux have the appropriate version.

For archlinux on the RCE:
pacman -S autoconf automake pkg-config git

----------------------------------------------------------
Install and compile libzeromq, czmq & zyre
----------------------------------------------------------
Choose your install path for zeromq. This will include a
base directory, a src directory and a python directory for
the resulting python wrappers. The install scripts will create
lib and bin sub-directories within this base.

For example on the RCE:

> mkdir /mnt/host/zeromq/
> mkdir /mnt/host/zeromq/python/
> mkdir /mnt/host/zeromq/src/
> cd /mnt/host/zeromq/src/

Get and compile zeromq:

> git clone https://github.com/zeromq/libzmq.git
> cd libzmq
> ./autogen.sh
> ./configure --prefix=/mnt/host/zeromq/
> make install

Get and compile czmq (high level wrappers for libzmq):

> cd ..
> git clone https://github.com/zeromq/czmq.git
> cd czmq
> ./autogen.sh
> export libzmq_LIBS="-L/mnt/host/zeromq/lib/ -lzmq"
> export libzmq_CFLAGS="-I/mnt/host/zeromq/include/"
> ./configure --prefix=/mnt/host/zeromq/ --with-libzmq=/mnt/host/zeromq
> make install
> scp -r bindings/python/czmq ../../python/

Get and compile zyre:

> cd ..
> git clone https://github.com/zeromq/zyre.git
> cd zyre
> ./autogen.sh
> export czmq_LIBS="-L/mnt/host/zeromq/lib/ -lczmq"
> export czmq_CFLAGS="-I/mnt/host/zeromq/include/"
> ./configure --prefix=/mnt/host/zeromq --with-libczmq=/mnt/host/zeromq
> make install
> scp -r bindings/python/zyre ../../python/

