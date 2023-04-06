import logging
from typing import Dict

from agent import StoreAgent
from item import ServiceItem


class EventHandler: #用于处理event的对象和事件
    def __init__(self):
        self.handle_func = {
            "ADDED": self.add,
            "MODIFIED": self.modify,
            "DELETED": self.delete,
        }

    def handle(self, event: Dict, agent: StoreAgent):
        event_type = event["type"]
        metadata = event["raw_object"]["metadata"]
        spec = event["raw_object"]["spec"]

        name = metadata["name"]
        namespace = metadata["namespace"]
        version = metadata["resourceVersion"]

        ports = spec["ports"]
        
        logging.info(f"{event_type}, {name}")

        service = ServiceItem(name=name, namespace=namespace, version=version, ports=ports)
        self.handle_func[event_type](service, agent)
    
    def add(self, service: ServiceItem, agent: StoreAgent):
        pass

    def modify(self, service: ServiceItem, agent: StoreAgent):
        pass
    
    def delete(self, service: ServiceItem, agent: StoreAgent):
        pass