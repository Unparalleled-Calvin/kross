from typing import Dict, List


class PortItem:
    def __init__(self, name: str=None, protocol: str=None, port: int=None, targetPort: int=None, raw_object: dict=None):
        if raw_object is None:
            self.name = name
            self.protocol = protocol
            self.port = port
            self.targetPort = targetPort
        else:
            self.name = raw_object.get("name", None)
            self.protocol = raw_object["protocol"]
            self.port = raw_object["port"]
            self.targetPort = raw_object["targetPort"]

class IPItem:
    def __init__(self, clusterIP: str):
        self.clusterIP = clusterIP


class ServiceItem:
    def __init__(self, ports: List[PortItem]=None, clusterIP: IPItem=None, raw_object: Dict=None):
        if raw_object is None:
            self.ports = ports
            self.clusterIP = clusterIP
        else:
            self.ports = [PortItem(raw_object=i) for i in raw_object["ports"]]
            self.clusterIP = IPItem(clusterIP=raw_object["clusterIP"])
    