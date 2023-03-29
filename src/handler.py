import logging
from typing import Dict

from agent import EtcdAgent
from item import ServiceItem


class EventHandler: #用于处理event的对象和事件
    def __init__(self):
        pass

    def handle(self, event: Dict, edcd_agent: EtcdAgent):
        event_type = event["type"]
        raw_object = event["raw_object"]
        svc_name = raw_object['metadata']['name']
        spec = raw_object["spec"]
        
        logging.debug(f"{event_type}, {svc_name}")
        service = ServiceItem(raw_object=spec)