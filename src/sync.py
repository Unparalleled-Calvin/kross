import logging
import time

import etcd3
import kubernetes
import typing

import store


def pod_running_sync(v1: kubernetes.client.CoreV1Api, name: str, namespace: str="default", intersection: int=1, timeout=20):
    time_cnt = 0
    while time_cnt < timeout: #sync for pod running
        try:
            if v1.read_namespaced_pod(name=name, namespace=namespace).status.phase == "Running":
                break
        except Exception:
            pass
        time.sleep(intersection)
        time_cnt += intersection
    if time_cnt < timeout:
        logging.info(f"[Kross]pod {name} has been running")
    else:
        logging.info(f"[Kross]fail to sync whether pod {name} has been running in the given time.")

def etcd_running_sync(host: str, port: int, intersection: int=1, timeout=20):
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
    if time_cnt < timeout:
        logging.info(f"[Kross]etcd {host}:{port} has been running")
    else:
        logging.info(f"[Kross]fail to sync whether etcd {host}:{port} has been running in the given time.")

def etcd_member_added_sync(etcd_agent: store.EtcdAgent, peerUrls: list, intersection: int=1, timeout=20):
    time_cnt = 0
    while time_cnt < timeout :
        try:
            etcd_agent.add_member(peerUrls) #actually the pod hasn't been running
        except etcd3.exceptions.ConnectionFailedError as e:
            logging.info(f"[Kross]retrying to add etcd member {peerUrls[0]} into cluster...")
            time.sleep(1)
        else:
            break
    if time_cnt < timeout:
        logging.info(f"[Kross]member has been added")
    else:
        logging.info(f"[Kross]fail to sync whether member has been added in the given time.")

def resource_deleted_sync(v1: kubernetes.client.CoreV1Api, resource: str, label_selector: str, namespace: str="default", intersection: int=1, timeout=20):
    time_cnt = 0
    while time_cnt < timeout:
        items = getattr(v1, f"list_namespaced_{resource}")(
            namespace=namespace,
            label_selector=label_selector
        ).items
        if len(items) != 0:
            time.sleep(intersection)
            time_cnt += intersection
        else:
            break
    if time_cnt < timeout:
        logging.info(f"[Kross]{resource} with {label_selector} has been deleted")
    else:
        logging.info(f"[Kross]fail to sync whether {resource} with {label_selector} has been deleted in the given time.")

def sync_template(target: object, obj: object, process: typing.Callable, intersection: int=1, timeout=20):
    time_cnt = 0
    while timeout is None or time_cnt < timeout:
        if process(obj) != target:
            time.sleep(intersection)
            time_cnt += intersection
        else:
            break

def acquire_etcd_lock(etcd_agent: store.EtcdAgent, lock_key: str="/kross/etcd/lock", result_key: str=None):
    client = etcd_agent.client
    if result_key is None:
        result_key = f"/kross/etcd/lock/result/{client._url}"
    client.transaction(
        compare=[client.transactions.value(lock_key) == "0"],
        success=[client.transactions.put(result_key, "1")],
        failure=[client.transactions.put(result_key, "0")]
    )
    _result, _ = etcd_agent.read(result_key)
    result = _result.decode()
    return result == "1"

def release_etcd_lock(etcd_agent: store.EtcdAgent, lock_key: str="/kross/etcd/lock", result_key: str=None):
    client = etcd_agent.client
    if result_key is None:
        result_key = f"/kross/etcd/lock/result/{client._url}"
    client.transaction(
        compare=[client.transactions.value(result_key) == "1"],
        success=[
            client.transactions.put(lock_key, "1"),
            client.transactions.put(result_key, "0")
        ],
        failure=[]
    )