import logging

from kubernetes import client, config, watch

import agent
import handler


def init_logger(filename=None, filemode=None, format=None, level=logging.DEBUG):
    if filename is None:
        filename = "kross.log"
    if format is None:
        format = "%(asctime)s[%(levelname)s]: %(message)s"
    if filemode is None:
        filemode = "a"
    datefmt = "%Y/%m/%d %H:%M:%S"
    logging.basicConfig(filename=filename, filemode=filemode, format=format, datefmt=datefmt, level=level)

def init_kubeAPI():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    w = watch.Watch()
    return v1, w

def main():
    init_logger()
    v1, w = init_kubeAPI()
    event_handler = handler.EventHandler()
    etcd_agent = agent.EtcdAgent()
    for event in w.stream(v1.list_service_for_all_namespaces, watch=True, _continue=False):
        # try:
        event_handler.handle(event, etcd_agent)
        # except Exception as e:
            # logging.error(e)
            # w.stop()

main()