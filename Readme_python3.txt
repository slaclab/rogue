# Python3 install

Choose an install location:

> mkdir /path/to/python/3.6.1
> mkdir /path/to/python/3.6.1/src/

Download and install python3

> cd /path/to/python/3.6.1/src
> wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tgz
> tar -xvvzpf Python-3.6.1.tar.xz
> cd Python-3.6.1
> ./configure --prefix=/path/to/python/3.6.1 --enable-shared
> make 
> make install

Setup environment

Add /path/to/python/3.6.1/bin to your $PATH
Add /path/to/python/3.6.1/lib to your $LD_LIBRARY_PATH

It is recommended to create a settings.csh and settings.sh file in
/path/to/python/3.6.1 to allow users to add this specific python
install to their environment when needed.

Install sip

> cd /path/to/python/3.6.1/src/
> wget https://sourceforge.net/projects/pyqt/files/sip/sip-4.19.2/sip-4.19.2.tar.gz
> tar -xvvzpf sip-4.19.2.tar.gz
> cd sip-4.19.2
> python3 configure.py 
> make 
> make install

Install pyqt4 (if you want a local GUI)

> cd /path/to/python/3.6.1/src/
> wget https://downloads.sourceforge.net/project/pyqt/PyQt4/PyQt-4.12/PyQt4_gpl_x11-4.12.tar.gz
> tar -xvvzpf PyQt4_gpl_x11-4.12.tar.gz
> cd PyQt4_gpl_x11-4.12
> python3 configure-ng.py --qmake=/usr/bin/qmake-qt4 --assume-shared
> make 
> make install

Install swig

> yum install pcre-devel (or equivelent)
> cd /path/to/python/3.6.1/src/
> wget http://downloads.sourceforge.net/project/swig/swig/swig-3.0.12/swig-3.0.12.tar.gz
> tar -xvvzpf swig-3.0.12.tar.gz
> cd swig-3.0.12
> ./configure --prefix=/path/to/python/3.6.1/ 
> make
> make install

Epics wrappers for python

> source /path/to/epics/settings.csh (or settings.sh)
> pip3 install pcaspy

Zeromq wrappers for python (see Readme_zeromq.txt)

> source /path/to/zeromq/settings.csh (or settings.sh)
> pip3 install pyzmq

Other python packages

> pip3 install ipython
> pip3 install PyYAML
> pip3 install Pyro4 
> pip3 install parse 
> pip3 install recordclass
> pip3 install click

