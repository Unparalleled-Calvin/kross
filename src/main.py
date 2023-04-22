import logging
import threading

import kubernetes
import yaml

import handler
import peer
import sanitize
import server
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

def init_kross(v1: kubernetes.client.CoreV1Api, local_etcd_agent: store.EtcdAgent, peers: list=None, base_port: int=32379, namespace: str="default") -> store.EtcdAgent:
    kross_etcd_agent = peer.handle_peers(v1=v1, local_etcd_agent=local_etcd_agent, peers=peers, base_port=base_port, namespace=namespace)
    return kross_etcd_agent

def init_handler(v1: kubernetes.client.CoreV1Api, w: kubernetes.watch.Watch, store_agent: store.StoreAgent):
    handler_thread = threading.Thread(target=handler.start_handler, kwargs={"v1": v1, "w": w, "store_agent": store_agent})
    handler_thread.start()
    return handler_thread

# def quit_elegantly(v1: kubernetes.client.CoreV1Api, store_agent: store.StoreAgent, peers: list=None, namespace: str="default"):
#     peer.quit_peers(v1=v1, store_agent=store_agent, namespace=namespace)
#     sanitize.sanitize(v1=v1, store_agent=store_agent, namespace=namespace)

def main():
    kross_config = load_config("config.yaml")
    init_logger(**kross_config["log"])
    v1, w = init_kubeAPI()
    local_etcd_agent = store.EtcdAgent(**kross_config["etcd"])
    sanitize.sanitize(v1, local_etcd_agent)
    kross_etcd_agent = init_kross(v1=v1, local_etcd_agent=local_etcd_agent, **kross_config["kross"], namespace="default")
    init_handler(v1=v1, w=w, store_agent=kross_etcd_agent)
    server.start_server(local_etcd_agent=local_etcd_agent, kross_etcd_agent=kross_etcd_agent, **kross_config["server"])
    # quit_elegantly()

main()