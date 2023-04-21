import logging
import threading

import kubernetes
import yaml

import handler
import peer
import sanitize
import server
import store
import util


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
    apps_v1 = kubernetes.client.AppsV1Api()
    w = kubernetes.watch.Watch()
    return v1, apps_v1, w

def init_kross(v1: kubernetes.client.CoreV1Api, store_agent: store.StoreAgent, peers: list=None, base_port: int=32379, namespace: str="default") -> store.EtcdAgent:
    pod_info = peer.handle_peers(v1=v1, store_agent=store_agent, peers=peers, base_port=base_port, namespace=namespace)
    util.pod_running_sync(v1=v1, name=pod_info["name"], namespace=namespace)
    kross_etcd_agent = store.EtcdAgent(host=pod_info["host"], port=pod_info["client_node_port"])
    return kross_etcd_agent

def init_server(local_etcd_agent: store.EtcdAgent, kross_etcd_agent: store.EtcdAgent, port: int=7890):
    server_thread = threading.Thread(target=server.start_server, kwargs={"port": port, "local_etcd_agent": local_etcd_agent, "kross_etcd_agent": kross_etcd_agent})
    server_thread.start()

def main():
    kross_config = load_config("config.yaml")
    init_logger(**kross_config["log"])
    v1, apps_v1, w = init_kubeAPI()
    local_etcd_agent = store.EtcdAgent(**kross_config["etcd"])
    # sanitize.sanitize(v1, local_etcd_agent)
    kross_etcd_agent = init_kross(v1=v1, store_agent=local_etcd_agent, **kross_config["kross"], namespace="default")
    init_server(local_etcd_agent=local_etcd_agent, kross_etcd_agent=kross_etcd_agent, **kross_config["server"])
    event_handler = handler.EventHandler(store_agent=local_etcd_agent)
    for event in w.stream(v1.list_service_for_all_namespaces, watch=True, _continue=False):
        event_handler.handle(event)

main()