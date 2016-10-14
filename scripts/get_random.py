#!/usr/bin/env python

from pcaspy import SimpleServer, Driver
import random

prefix = 'MTEST:'
pvdb = {
    'RAND' : {
        'prec' : 3,
        'scan' : 1,
        'count': 10,
    },
}

class myDriver(Driver):
    def __init__(self):
        super(myDriver, self).__init__()

    def read(self, reason):
        if reason == 'RAND':
            value = [random.random() for i in range(10)]
        else:
            value = self.getParam(reason)
        return value

if __name__ == '__main__':
    server = SimpleServer()
    server.createPV(prefix, pvdb)
    driver = myDriver()

    # process CA transactions
    while True:
        server.process(0.1)
