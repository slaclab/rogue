Compiling zeromq:

----------------------------------------------------------
Required Packages
----------------------------------------------------------
A recent version of autoconf is required. This version is
not available on rhel6. A recent version of autoconf is 
installed at slac at:

/afs/slac.stanford.edu/g/reseng/vol11/autoconf/autoconf-2.69

You need to either install autoconf, the the above version
or download it and compile it on your own.

For archlinux on the RCE:
pacman -S autoconf automake pkg-config git

----------------------------------------------------------
Install and compile libzeromq, czmq & zyre
----------------------------------------------------------
Choose your install path for zeromq, with a src and 
python library directory.
For example on the RCE:

mkdir /mnt/host/zeromq/
mkdir /mnt/host/zeromq/python/
mkdir /mnt/host/zeromq/src/
cd /mnt/host/zeromq/src/

git clone https://github.com/zeromq/libzmq.git
cd libzmq
./autogen.sh
./configure --prefix=/mnt/host/zeromq/
make install

cd ..
git clone https://github.com/zeromq/czmq.git
cd czmq
./autogen.sh
export libzmq_LIBS="-L/mnt/host/zeromq/lib/ -lzmq"
export libzmq_CFLAGS="-I/mnt/host/zeromq/include/"
./configure --prefix=/mnt/host/zeromq/ --with-libzmq=/mnt/host/zeromq
make install
scp -r bindings/python/czmq ../../python/

cd ..
git clone https://github.com/zeromq/zyre.git
cd zyre
./autogen.sh
export czmq_LIBS="-L/mnt/host/zeromq/lib/ -lczmq"
export czmq_CFLAGS="-I/mnt/host/zeromq/include/"
./configure --prefix=/mnt/host/zeromq --with-libczmq=/mnt/host/zeromq
make install
scp -r bindings/python/zyre ../../python/

