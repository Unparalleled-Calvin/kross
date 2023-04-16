import json
import logging
import typing

import item
import path
import store


class EventHandler:
    def __init__(self, store_agent: store.StoreAgent):
        self.handle_func = {
            "ADDED": self.event_add,
            "MODIFIED": self.event_modify,
            "DELETED": self.event_delete,
        }
        self.store_agent = store_agent

    def handle(self, event: typing.Dict):
        event_type = event["type"]
        metadata = event["raw_object"]["metadata"]
        spec = event["raw_object"]["spec"]

        name = metadata["name"]
        namespace = metadata["namespace"]
        version = metadata["resourceVersion"]
        ports = spec["ports"]
        annotations = metadata.get("annotations", {})
        kross = annotations.get("kross", "{}")
        
        if spec["type"] != "NodePort": #only process NodePort Service
            return 
        
        logging.info(f"{event_type}, {name}")

        service = item.ServiceItem(name=name, namespace=namespace, version=version, ports=ports)
        service = self.modify_svc(service, kross)

        if len(service.ports):
            self.handle_func[event_type](service)

    def modify_svc(self, service: item.ServiceItem, kross: str): #select exposed ports and modify the protocol
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

    def event_add(self, service: item.ServiceItem):
        self.store_agent.write(path.svc_path(service), service)

    def event_modify(self, service: item.ServiceItem):
        _service, _ = self.store_agent.read(path.svc_path(service))
        _service = item.ServiceItem.decode(_service)
        self.store_agent.write(path.svc_path(service), service)
    
    def event_delete(self, service: item.ServiceItem):
        self.store_agent.delete(path.svc_path(service))
    