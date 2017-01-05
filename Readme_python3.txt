# Python3 support for rogue

Choose an install location:

> mkdir /path/to/python/3.5.2
> mkdir /path/to/python/3.5.2/src/

Download and install python3

> cd /path/to/python/3.5.2/src
> wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz
> tar -xvvzpf Python-3.5.2.tar.xz
> cd Python-3.5.2
> ./configure --prefix=/path/to/python/3.5.2 --enable-shared
> make 
> make install

Setup environment

Add /path/to/python/3.5.2/bin to your $PATH
Add /path/to/python/3.5.2/lib to your $LD_LIBRARY_PATH

It is recommended to create a settings.csh and settings.sh file in
/path/to/python/3.5.2 to allow users to add this specific python
install to their environment when needed.

Install sip

> cd /path/to/python/3.5.2/src/
> wget https://sourceforge.net/projects/pyqt/files/sip/sip-4.18.1/sip-4.18.1.tar.gz
> tar -xvvzpf sip-4.18.1.tar.gz
> cd sip-4.18.1
> python3 configure.py 
> make 
> make install

Install pyqt4

> cd /path/to/python/3.5.2/src/
> wget http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-4.11.4/PyQt-x11-gpl-4.11.4.tar.gz
> tar -xvvzpf PyQt-x11-gpl-4.11.4.tar.gz
> cd PyQt-x11-gpl-4.11.4
> python3 configure-ng.py --qmake=/usr/bin/qmake-qt4 --assume-shared
> make 
> make install

Install swig

> yum install pcre-devel (or equivelent)
> cd /path/to/python/3.5.2/src/
> wget http://downloads.sourceforge.net/project/swig/swig/swig-3.0.10/swig-3.0.10.tar.gz
> tar -xvvzpf swig-3.0.10.tar.gz
> cd swig-3.0.10
> ./configure --prefix=/path/to/python/3.5.2/ 
> make
> make install

Epics wrappers for python

> source /path/to/epics/settings.csh (or settings.sh)
> pip3 install pcaspy

It seems there is a bug for python 3. Edit the file:
/path/to/python/3.5.2/lib/python3.5/site-packages/pcaspy/cas.py
adding the following import statement to the top of the file:
import builtins

Zeromq wrappers for python (see Readme_zeromq.txt)

> source /path/to/zeromq/settings.csh (or settings.sh)
> pip3 install pyzmq
> pip3 install https://github.com/zeromq/pyre/archive/master.zip

Other python packages

> pip3 install ipython
> pip3 install PyYAML

