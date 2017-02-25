# Python2 support for rogue

Choose an install location:

> mkdir /path/to/python/2.7.13
> mkdir /path/to/python/2.7.13/src/

Download and install python2

> cd /path/to/python/2.7.13/src/
> wget https://www.python.org/ftp/python/2.7.13/Python-2.7.13.tar.xz
> tar -xvvzpf Python-2.7.13.tar.xz
> cd Python-2.7.13
> ./configure --prefix=/path/to/python/2.7.13 --enable-shared
> make 
> make install

Setup environment

Add /path/to/python/2.7.13/bin to your $PATH
Add /path/to/python/2.7.13/lib to your $LD_LIBRARY_PATH

It is recommended to create a settings.csh and settings.sh file in
/path/to/python/2.7.13 to allow users to add this specific python
install to their environment when needed.

Install sip

> cd /path/to/python/2.7.13/src/
> wget https://sourceforge.net/projects/pyqt/files/sip/sip-4.18.1/sip-4.18.1.tar.gz
> tar -xvvzpf sip-4.18.1.tar.gz
> cd sip-4.18.1
> python2 configure.py 
> make 
> make install

Install pyqt4 (if you want a local GUI)

> cd /path/to/python/2.7.13/src/
> wget http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-4.11.4/PyQt-x11-gpl-4.11.4.tar.gz
> tar -xvvzpf PyQt-x11-gpl-4.11.4.tar.gz
> cd PyQt-x11-gpl-4.11
> python2 configure-ng.py --qmake=/usr/bin/qmake-qt4 --assume-shared
> edit QtGui/sipQtGuiQAbstractPrintDialog.cpp and remove the line containing 'PrintCurrentPage'
> make 
> make install

Install swig

> yum install pcre-devel (or equivilent)
> cd /path/to/python/2.7.13/src/
> wget http://downloads.sourceforge.net/project/swig/swig/swig-3.0.10/swig-3.0.10.tar.gz
> tar -xvvzpf swig-3.0.10.tar.gz
> cd swig-3.0.10
> ./configure --prefix=/path/to/python/2.7.13/ 
> make
> make install

Install pip

> cd /path/to/python/2.7.13/src/
> wget https://bootstrap.pypa.io/get-pip.py
> python2 get-pip.py

Re-source your environment here to update $PATH with new binaries.

Epics wrappers for python

> source /path/to/epics/settings.csh (or settings.sh)
> pip2 install pcaspy

Zeromq wrappers for python (see Readme_zeromq.txt)

> source /path/to/zeromq/settings.csh (or settings.sh)
> pip2 install pyzmq
> pip2 install https://github.com/zeromq/pyre/archive/master.zip

Other python packages

> pip2 install ipython
> pip2 install PyYAML

