import logging
import time

import etcd3
from kubernetes import client

import store


def pod_running_sync(v1: client.CoreV1Api, name: str, namespace: str="default", intersection: int=0.5, timeout=5):
    time_cnt = 0
    while time_cnt < timeout and v1.read_namespaced_pod(name=name, namespace=namespace).status.phase != "Running": #sync for pod running
        time.sleep(intersection)
        time_cnt += intersection

def etcd_running_sync(host: str, port: int, intersection: int=0.5, timeout=10):
    client = etcd3.client(host=host, port=port)
    time_cnt = 0
    while time_cnt < timeout:
        try:
            client.status()
        except Exception as e:
            time.sleep(intersection)
            time_cnt += intersection
        else:
            break

def etcd_member_added_sync(etcd_agent: store.EtcdAgent, target_num: int, intersection: int=0.5, timeout=5):
    time_cnt = 0
    while time_cnt < timeout and len(etcd_agent.members) < target_num:
        time.sleep(intersection)
        time_cnt += intersection
