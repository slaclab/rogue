#-----------------------------------------------------------------------------
# Title      : PyRogue Simple ZMQ Client for Rogue
#-----------------------------------------------------------------------------
# To use in Matlab first you need the zmq package in your
# python installation:
#
# > pip install zmq
# > pip install matlab
#
# You then need to set the appropriate flags in Matlab to load the zmq module:
#
# >> py.sys.setdlopenflags(int32(bitor(2, 8)));
#
# c = py.SimpleClient.SimpleClient("localhost",9099);
# c.get("dummyTree.Time")
#
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import zmq
import threading


class SimpleClient(object):
    """
    A lightweight client inerface for Rogue. This can be used in
    scripts or as an interface to Rogue in matlab. For a more
    powerfull, tree access capable client. Please see the
    VirtualClient class.

    To use in Matlab first you need the zmq package in your  python installation:

    > pip install zmq

    > pip install matlab

    You then need to set the appropriate flags in Matlab to load the zmq module:

    >> py.sys.setdlopenflags(int32(bitor(2, 8)));

    >> c = py.SimpleClient.SimpleClient("localhost",9099);

    >> c.get("dummyTree.Time")

    Parameters
    ----------
    addr : str
        host address

    port : int
        host port

    cb : obj
        call back function for variable updates, in the form func(path,value)

    """

    def __init__(self, addr="localhost", port=9099, cb=None):
        sport = port
        rport = port + 1
        self._ctx = zmq.Context()

        self._req = self._ctx.socket(zmq.REQ)
        self._req.connect(f'tcp://{addr}:{rport}')

        if cb:
            self._cb  = cb
            self._sub = self._ctx.socket(zmq.SUB)
            self._sub.connect(f'tcp://{addr}:{sport}')
            self._runEn = True
            self._subThread = threading.Thread(target=self._listen)
            self._subThread.start()

    def _stop(self):
        """
        Stop the SimpleClient interface.
        This must be called if not not using the SimpleClient in a context
        """

        self._runEn = False

    def _listen(self):
        self._sub.setsockopt(zmq.SUBSCRIBE,"".encode('utf-8'))

        while self._runEn:
            d = self._sub.recv_pyobj()

            for k,val in d.items():
                self._cb(k,val)


    def _remoteAttr(self,path,attr,*args,**kwargs):
        msg = {'path':path,
               'attr':attr,
               'args':args,
               'kwargs':kwargs}

        try:
            self._req.send_pyobj(msg)
            resp = self._req.recv_pyobj()
        except Exception as e:
            raise Exception(f"ZMQ Interface Exception: {e}")

        if isinstance(resp,Exception):
            raise resp

        return resp

    def get(self,path):
        """
        Get a variable value, initating a read

        Parameters
        ----------
        path : str
            Path of the variable to return a value for

        Returns
        -------
        obj
            Variable value in native form

        """
        return self._remoteAttr(path, 'get')

    def getDisp(self,path):
        """
        Get a variable value, in string form, initating a read

        Parameters
        ----------
        path : str
            Path of the variable to return a value for

        Returns
        -------
        str
            Variable value in string form

        """
        return self._remoteAttr(path, 'getDisp')

    def value(self,path):
        """
        Get a variable value, without initating a read

        Parameters
        ----------
        path : str
            Path of the variable to return a value for

        Returns
        -------
        obj
            Variable value

        """
        return self._remoteAttr(path, 'value')

    def valueDisp(self,path):
        """
        Get a variable value, in string form, without initating a read

        Parameters
        ----------
        path : str
            Path of the variable to return a value for

        Returns
        -------
        str
            Variable value in string form

        """
        return self._remoteAttr(path, 'valueDisp')

    def set(self,path,value):
        """
        Set a variable value, using its native type

        Parameters
        ----------
        path : str
            Path of the variable to set

        value : obj
            Value to set
        """
        return self._remoteAttr(path, 'set', value)

    def setDisp(self,path,value):
        """
        Set a variable value, using a string representation

        Parameters
        ----------
        path : str
            Path of the variable to set

        value : str
            Value to set
        """
        return self._remoteAttr(path, 'setDisp', value)

    def exec(self,path,arg=None):
        """
        Call a command, with the optional arg

        Parameters
        ----------
        path : str
            Path of the variable to set

        arg : obj
            Command argument, in native or string form

        Returns
        -------
        obj
            Return value of the underlying command
        """
        return self._remoteAttr(path, '__call__', arg)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._stop()
