import json
import logging
import time
import typing

import kubernetes

import item
import path
import peer
import store
import sync


class EventHandler:
    def __init__(self, kross_etcd_agent: store.StoreAgent, local_etcd_agent: store.StoreAgent, hosts: list):
        self.handle_func = {
            "ADDED": self.event_add,
            "MODIFIED": self.event_modify,
            "DELETED": self.event_delete,
        }
        self.kross_etcd_agent = kross_etcd_agent
        self.local_etcd_agent = local_etcd_agent
        self.hosts = hosts

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
        
        logging.debug(f"[Kross]{event_type} event: {name}")

        service = item.ServiceItem(name=name, namespace=namespace, version=version, ports=ports)
        service = self.modify_svc(service, kross)

        self.handle_func[event_type](service)

    def modify_svc(self, service: item.ServiceItem, kross: str): #select exposed ports and modify the protocol
        try:
            kross = json.loads(kross)
            ports = kross["exposure"]
        except KeyError:
            ports = []
            logging.debug(f"[Kross]Service {service.name} dosen't have proper kross annotation fields. Use '{{}}' instead.")
        except json.JSONDecodeError:
            ports = []
            logging.error(f"[Kross]Fail to decode kross: {kross} by json format. Use '{{}}' instead.")
        service.ports = list(filter(lambda port: port.port in ports or port.name in ports, service.ports))
        return service

    def event_add(self, service: item.ServiceItem):
        if len(service.ports) > 0:
            for host in self.hosts:
                self.kross_etcd_agent.write(path.svc_path(service.name, host), service)
            self.local_etcd_agent.write(path.svc_path(service.name, None), "")
            logging.info(f"[Kross]Service {service.name} updated.")

    def event_modify(self, service: item.ServiceItem):
        if len(service.ports) > 0:
            for host in self.hosts:
                self.kross_etcd_agent.write(path.svc_path(service.name, host), service)
            self.local_etcd_agent.write(path.svc_path(service.name, None), "")
            logging.info(f"[Kross]Service {service.name} updated.")
        else:
            for host in self.hosts:
                self.kross_etcd_agent.delete(path.svc_path(service.name, host))
            self.local_etcd_agent.delete(path.svc_path(service.name, None))
            logging.info(f"[Kross]Service {service.name} deleted.")
    
    def event_delete(self, service: item.ServiceItem):
        for host in self.hosts:
            self.kross_etcd_agent.delete(path.svc_path(service.name, host))
        self.local_etcd_agent.delete(path.svc_path(service.name, None))
        logging.info(f"[Kross]Service {service.name} deleted.")

def start_handler(v1: kubernetes.client.CoreV1Api, w: kubernetes.watch.Watch, kross_etcd_agent: store.StoreAgent, local_etcd_agent: store.StoreAgent):
    hosts = peer.get_hosts(v1)
    time.sleep(2)
    sync.write_available_sync(etcd_agent=kross_etcd_agent)
    sync.write_available_sync(etcd_agent=local_etcd_agent)
    event_handler = EventHandler(kross_etcd_agent=kross_etcd_agent, local_etcd_agent=local_etcd_agent, hosts=hosts)
    for event in w.stream(v1.list_service_for_all_namespaces, watch=True, _continue=False):
        event_handler.handle(event)