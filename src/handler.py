import json
import logging
from typing import Dict, List, Union

from item import ServiceItem, PortItem
from store import StoreAgent


def svc_path(service: ServiceItem=None): #records for svc in local cluster
    return f"/kross/svc/{service.name}"

class EventHandler:
    def __init__(self, store_agent: StoreAgent):
        self.handle_func = {
            "ADDED": self.event_add,
            "MODIFIED": self.event_modify,
            "DELETED": self.event_delete,
        }
        self.store_agent = store_agent

    def handle(self, event: Dict):
        event_type = event["type"]
        metadata = event["raw_object"]["metadata"]
        spec = event["raw_object"]["spec"]

        name = metadata["name"]
        namespace = metadata["namespace"]
        version = metadata["resourceVersion"]
        ports = spec["ports"]
        annotations = metadata.get("annotations", {})
        kross = annotations.get("kross", "{}")
        
        logging.info(f"{event_type}, {name}")

        if name == "nginx-svc":
            with open("c.json", "w") as f:
                json.dump(event["raw_object"], f)

        service = ServiceItem(name=name, namespace=namespace, version=version, ports=ports)
        service = self.modify_svc(service, kross)
        
        if len(service.ports):
            self.handle_func[event_type](service)

    def modify_svc(self, service: ServiceItem, kross: str): #select exposed ports and modify the protocol
        try:
            kross = json.loads(kross)
            ports = kross["exposure"]
        except KeyError:
            ports = []
            logging.debug(f"Service {service.name} dosen't have proper kross annotation fields. Use '{{}}' instead.")
        except json.JSONDecodeError:
            ports = []
            logging.error(f"Fail to decode kross: {kross} by json format. Use '{{}}' instead.")
        service.ports = list(filter(lambda port: port.port in ports or port.name in ports, service.ports))
        return service

    def event_add(self, service: ServiceItem):
        self.store_agent.write(svc_path(service), service)

    def event_modify(self, service: ServiceItem):
        _service, _ = self.store_agent.read(svc_path(service))
        _service = ServiceItem.decode(_service)
        self.store_agent.write(svc_path(service), service)
    
    def event_delete(self, service: ServiceItem):
        self.store_agent.delete(svc_path(service))
    