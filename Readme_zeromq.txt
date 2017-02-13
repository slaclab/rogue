# ZeroMq

Zeromq is optional. It is only needed if you choose to use 
the mesh networking features of rogue or the simulation
link library.

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

