
import pyrogue

from typing import Union
import copy


class iocBuilder():
    """
    """
    def __init__(self, root: pyrogue.Root): 
        
        self.record_dict = {}
        self.device_name = root.name
        self.root = root

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
                name = self.convertToEpicsName(node.path)
                builder.aOut(name, 
                            initial_value=1, 
                            always_update=True,
                            on_update_name=lambda v, n : self.setVariable(self.root, n, v))

            else: print(node)
            #elif isinstance(node, pyrogue.Device):
        
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
