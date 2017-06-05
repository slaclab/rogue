import pyrogue as pr
import rogue.interfaces.memory

class PgpCardDevice(pr.Device):
    def __init__(self, pgpCard, **kwargs):
        super(self.__class__, self).__init__(**kwargs)

        self._pgpCard = pgpCard

        def info(attr):
            def get(dev, var):
                return getattr(self._pgpCard.getStatus(), attr)
            return get

        self.add((
            pr.Variable(name='cellErrCnt', base='hex', mode='RO', getFunction=info('cellErrCnt')),
            pr.Variable(name='fifoErr', base='bool', mode='RO', getFunction=info('fifoErr')),
            pr.Variable(name='lane', base='hex', mode='RO', getFunction=info('lane')),
            pr.Variable(name='linkDownCnt', base='hex', mode='RO', getFunction=info('linkDownCnt')),
            pr.Variable(name='linkErrCnt', base='hex', mode='RO', getFunction=info('linkErrCnt')),
            pr.Variable(name='locLinkReady', base='bool', mode='RO', getFunction=info('locLinkReady')),
            pr.Variable(name='loopBack', base='hex', mode='RO', getFunction=info('loopBack')),
            pr.Variable(name='remBuffStatus', base='hex', mode='RO', getFunction=info('remBuffStatus')),
            pr.Variable(name='remData', base='hex', mode='RO', getFunction=info('remData')),
            pr.Variable(name='remLinkReady', base='bool', mode='RO', getFunction=info('remLinkReady')),
            pr.Variable(name='rxCount', base='hex', mode='RO', getFunction=info('rxCount')),
            pr.Variable(name='rxReady', base='bool', mode='RO', getFunction=info('rxReady')),
            pr.Variable(name='txReady', base='bool', mode='RO', getFunction=info('txReady'))))


    
    def _backgroundTransaction(self, type):
        if type == rogue.interfaces.memory.Read:
            for v in self.variables.values():
                v.get()
