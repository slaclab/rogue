
import pyrogue

from typing import Union
import copy

import numpy as np
import matplotlib
from epicsdbbuilder import WriteRecords

class iocBuilder():
    """
    """
    def __init__(self, root: pyrogue.Root): 
        
        self.device_name = root.name
        self.root = root
        self.built = False
        self.func = {
            int.__name__ : 'aOut',
            str.__name__: 'stringOut',
            bool.__name__: 'boolOut',
            float.__name__: 'aOut',
        }

        from softioc import softioc, builder
        self.running = False
        builder.SetDeviceName(self.device_name)
        node_list = root.nodeList
        for node in node_list:
            if isinstance(node, pyrogue._Command.BaseCommand): continue
            elif isinstance(node, pyrogue._Device.EnableVariable):
                name = self.convertToEpicsName(node.path)
                builder.aOut(name, 
                            initial_value=1, 
                            always_update=True,
                            on_update_name=lambda v, n : self.setVariable(self.root, n, v))
            elif isinstance(node, pyrogue._Variable.BaseVariable):
                self.buildRecord(builder, node)
                #name = self.convertToEpicsName(node.path)
                #builder.aOut(name, 
                #            initial_value=1, 
                #            always_update=True,
                #            on_update_name=lambda v, n : self.setVariable(self.root, n, v))

            else: print(node)
            #elif isinstance(node, pyrogue.Device):
       
        WriteRecords('%s.db' % self.device_name)
        builder.LoadDatabase()

    def start(self):
        if not self.running:
            from softioc import softioc, asyncio_dispatcher
            dispatcher = asyncio_dispatcher.AsyncioDispatcher()
            softioc.iocInit(dispatcher)
            self.running = True

    def convertToEpicsName(self, path : str) -> str :
        name = path.replace(self.device_name+'.', '')
        name = name.replace('.',':')
        return name

    def setVariable(self, root: pyrogue.Root, name : str, value : Union[int, float]):
        print(name)
        path = name.replace(':','.')
        print(path)
        root.getNode(path).set(value)

    def buildRecord(self, builder, node: pyrogue.Node):
        name = self.convertToEpicsName(node.path)
        if (type(node.get()) is str): return
        if isinstance(node.get(), np.ndarray): return
        if isinstance(node.get(), list): return
        if isinstance(node.get(), matplotlib.pyplot.Figure): return
        print(name)
        print(type(node.get()).__name__)
        getattr(builder, 
                self.func[type(node.get()).__name__])(
                        name, 
                        initial_value=node.get(), 
                        always_update=True, 
                        on_update_name=lambda v, n : self.setVariable(self.root, n, v))


