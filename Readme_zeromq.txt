# ZeroMq

Choose an install location:

> mkdir /path/to/zeromq/4.2.0
> mkdir /path/to/zeromq/4.2.0/src/

Zeromq libraries

> cd /path/to/zeromq/4.2.0/src/
> wget https://github.com/zeromq/libzmq/releases/download/v4.2.0/zeromq-4.2.0.tar.gz
> tar -xvvzpf zeromq-4.2.0.tar.gz
> cd zeromq-4.2.0
> ./autogen.sh
> ./configure --prefix=/path/to/zeromq/4.2.0/
> make 
> make install

Setup environment

Add /path/to/zeromq/4.2.0/bin to your $PATH
Add /path/to/zeromq/4.2.0/lib to your $LD_LIBRARY_PATH

It is recommended to create a settings.csh and settings.sh file in
/path/to/zeromq/4.2.0 to allow users to add this specific python
install to their environment when needed. ZEROMQ_PATH should be set
to allow makefiles to include the proper include files and libraries.











------------------------------------
Old Notes
------------------------------------



Get and compile czmq (high level wrappers for libzmq):

> cd ..
> git clone https://github.com/zeromq/czmq.git
> cd czmq
> ./autogen.sh
> export libzmq_LIBS="-L/mnt/host/zeromq/4.2.0/lib/ -lzmq"
> export libzmq_CFLAGS="-I/mnt/host/zeromq/4.2.0/include/"
> ./configure --prefix=/mnt/host/zeromq/4.2.0 --with-libzmq=/mnt/host/zeromq/4.2.0
> make 
> make install
> scp -r bindings/python/czmq ../../python/


Setup environment

Add /path/to/python/2.7.13/bin to your $PATH
Add /path/to/python/2.7.13/lib to your $LD_LIBRARY_PATH

It is recommended to create a settings.csh and settings.sh file in
/path/to/python/2.7.13 to allow users to add this specific python
install to their environment when needed.



Get and compile zyre:

> cd ..
> git clone https://github.com/zeromq/zyre.git
> cd zyre
> ./autogen.sh
> export czmq_LIBS="-L/mnt/host/zeromq/lib/ -lczmq"
> export czmq_CFLAGS="-I/mnt/host/zeromq/include/"
> ./configure --prefix=/mnt/host/zeromq --with-libczmq=/mnt/host/zeromq
> make 
> make install
> scp -r bindings/python/zyre ../../python/

