
import pyrogue

from typing import Union

import numpy as np
import matplotlib

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
            np.ndarray.__name__: 'WaveformOut',
            list.__name__: 'WaveformOut'
        }

        self.running = False
        
        from softioc import softioc, builder
        
        # Set the record prefix
        builder.SetDeviceName(self.device_name)
      
        for node in root.nodeList:
            if isinstance(node, pyrogue._Command.BaseCommand): 
                # Commands will be turned into RPC's
                continue
            elif isinstance(node, pyrogue._Variable.BaseVariable):
                self.buildRecord(builder, node)
            else: print(node)
       
        builder.LoadDatabase()

    def start(self):
        if not self.running:
            from softioc import softioc, asyncio_dispatcher
            dispatcher = asyncio_dispatcher.AsyncioDispatcher()
            softioc.iocInit(dispatcher)
            self.running = True

    def setVariable(self, name : str, value : Union[int, float]):
        path = name.replace(':','.')
        root.getNode(path).set(value)

    def buildRecord(self, builder, node: pyrogue.Node):
        
        # Convert the node path to a name compatible with EPICS. This requires
        # the removal of the ROOT node name which is already included when 
        # the database is loaded.
        record_name = node.path[len(self.device_name)+1:].replace('.',':')

        value = node.get()
        
        # The maximum number of characters supported by a string record is 40.
        # TODO: In this case, use a longStringOut
        if isinstance(value, str) and len(value) > 40:
            builder.longStringIn(record_name, 
                                  initial_value=value)

            return

        if isinstance(value, (np.ndarray, list)): 
            if np.array(value).ndim != 1: 
                print('Multi-dimensional arrays are not supported.')
            elif isinstance(np.array(value)[0], bool): 
                print('Bool type is not supported for waveforms.') 
            return

        if isinstance(node.get(), matplotlib.pyplot.Figure): return

        getattr(builder, 
                self.func[type(value).__name__])(
                    record_name, 
                    initial_value=value, 
                    always_update=True, 
                    on_update_name=lambda v, n : self.setVariable(n, v))


