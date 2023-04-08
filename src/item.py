import json
from typing import Any, Dict, List


class DictLikeItem:
    data = {}
    def __init__(self, data=None):
        self.data = {} if data is None else data
    
    def __getattr__(self, attr):
        if attr in self.data:
            return self.data[attr]
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")
    
    def __setattr__(self, attr: str, value: object):
        if attr in self.data:
            self.data[attr] = value
        else:
            self.__dict__[attr] = value

    def encode(self, encoding="utf-8"):
        return json.dumps(self.data).encode(encoding)
    
    @staticmethod
    def decode(item: str):
        data = json.loads(item)
        return DictLikeItem(data=data)

class PortItem(DictLikeItem):
    def __init__(self, name: str=None, protocol: str=None, port: int=None, nodePort: int=None, data: Any=None):
        super().__init__()
        if data is None:
            self.data["name"] = name
            self.data["protocol"] = protocol
            self.data["port"] = int(port)
            self.data["nodePort"] = nodePort if nodePort is None else int(nodePort)
        elif isinstance(data, PortItem):
            self.data.update(data.data)
        else:
            self.data["name"] = data.get("name", None) #name是可选项
            self.data["protocol"] = data["protocol"]
            self.data["port"] = int(data["port"])

            nodePort = data.get("nodePort", None)
            self.data["nodePort"] = nodePort if nodePort is None else int(nodePort)
    
    @staticmethod
    def decode(item):
        data = json.loads(item)
        return PortItem(data=data)

class ServiceItem(DictLikeItem):
    def __init__(self, name: str=None, namespace:str=None, version: str=None, ports: List[PortItem]=None, data: Any=None):
        super().__init__()
        if data is None:
            self.data["name"] = name
            self.data["namespace"] = namespace
            self.data["ports"] = [PortItem(data=port) for port in ports]
            self.data["version"] = version
        elif isinstance(data, ServiceItem):
            self.data.update(data.data)
        else:
            self.data["name"] = data["name"]
            self.data["namespace"] = data["namespace"]
            self.data["version"] = data["version"]
            self.data["ports"] = [PortItem(data=port) for port in data["ports"]]
    
    def encode(self, encoding="utf-8"):
        ports = self.ports
        self.ports = [port.data for port in ports]
        encoding = json.dumps(self.data).encode(encoding)
        self.ports = ports
        return encoding

    @staticmethod
    def decode(item):
        data = json.loads(item)
        return ServiceItem(data=data)
    
    def __str__(self):
        ports = self.ports
        self.ports = [port.data for port in ports]
        str = json.dumps(self.data)
        self.ports = ports
        return str