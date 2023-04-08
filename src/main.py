import logging

import kubernetes
import yaml

import handler
import store


def load_config(filename="config.yaml"):
    with open(filename, "r") as f:
        config = yaml.safe_load(f)
    return config

def init_logger(filename=None, filemode=None, format=None, level="DEBUG"):
    if filename is None:
        filename = "kross.log"
    if format is None:
        format = "%(asctime)s[%(levelname)s]: %(message)s"
    if filemode is None:
        filemode = "a"
    datefmt = "%Y/%m/%d %H:%M:%S"
    level = getattr(logging, level)
    logging.basicConfig(filename=filename, filemode=filemode, format=format, datefmt=datefmt, level=level)

def init_kubeAPI():
    kubernetes.config.load_config() #will load config file or incluster config automatically
    v1 = kubernetes.client.CoreV1Api()
    w = kubernetes.watch.Watch()
    return v1, w

def main():
    kross_config = load_config("config.yaml")
    init_logger(**kross_config["log"])
    v1, w = init_kubeAPI()
    etcd_agent = store.EtcdAgent(**kross_config["etcd"])
    event_handler = handler.EventHandler(store_agent=etcd_agent)
    for event in w.stream(v1.list_service_for_all_namespaces, watch=True, _continue=False):
        event_handler.handle(event)

main()