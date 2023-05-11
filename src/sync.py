import logging
import time
import typing

import etcd3
import kubernetes

import path
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
        logging.info(f"[Kross]Pod {name} has been running")
    else:
        logging.info(f"[Kross]Fail to sync whether pod {name} has been running in the given time.")

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
        logging.info(f"[Kross]Etcd {host}:{port} has been running")
    else:
        logging.info(f"[Kross]Fail to sync whether etcd {host}:{port} has been running in the given time.")

def etcd_member_added_sync(etcd_agent: store.EtcdAgent, peerUrls: list, intersection: int=1, timeout=20):
    time_cnt = 0
    while time_cnt < timeout :
        try:
            etcd_agent.add_member(peerUrls) #actually the pod hasn't been running
        except etcd3.exceptions.ConnectionFailedError as e:
            logging.info(f"[Kross]Retrying to add etcd member {peerUrls[0]} into cluster...")
            time.sleep(intersection)
            time_cnt += intersection
        else:
            break
    if time_cnt < timeout:
        logging.info(f"[Kross]Member has been added")
    else:
        logging.info(f"[Kross]Fail to sync whether member has been added in the given time.")

def etcd_member_removed_sync(member: etcd3.Member, intersection: int=1, timeout=20):
    time_cnt = 0
    while time_cnt < timeout :
        try:
            member.remove() #actually the pod hasn't been running
        except Exception as e:
            logging.info(f"[Kross]Retrying to remove etcd member {member.id} from cluster...")
            logging.debug(e)
            time.sleep(intersection)
            time_cnt += intersection
        else:
            break
    if time_cnt < timeout:
        logging.info(f"[Kross]Member has been removed")
    else:
        logging.info(f"[Kross]Fail to sync whether member has been removed in the given time.")

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
        logging.info(f"[Kross]Resources {resource} with {label_selector} have been deleted")
    else:
        logging.info(f"[Kross]Fail to sync whether {resource} with {label_selector} has been deleted in the given time.")

def sync_template(target: object, kwargs: dict, process: typing.Callable, intersection: int=1, timeout=20):
    time_cnt = 0
    while timeout is None or time_cnt < timeout:
        if process(**kwargs) != target:
            time.sleep(intersection)
            time_cnt += intersection
        else:
            break

def init_etcd_lock(etcd_agent: store.EtcdAgent, lock_key: str=None):
    if lock_key is None:
        lock_key = path.etcd_lock_path()
    etcd_agent.write(lock_key, "0") #"0" means the lock can be acquired

def try_to_acquire_etcd_lock_once(etcd_agent: store.EtcdAgent, lock_key: str=None, lock_result_key: str=None) -> bool:
    client = etcd_agent.client
    if lock_key is None:
        lock_key = path.etcd_lock_path()
    if lock_result_key is None:
        lock_result_key = path.etcd_lock_result_path(client._url)
    client.transaction(
        compare=[client.transactions.value(lock_key) == "0"],
        success=[
            client.transactions.put(lock_result_key, "1"),
            client.transactions.put(lock_key, "1")
        ],
        failure=[]
    )
    _result, _ = etcd_agent.read(lock_result_key) #even through lock_key and lock_result_key are both 1 before the transaction, it also works
    result = _result.decode()
    success = result == "1"
    if success:
        logging.info(f"[Kross]Lock acquired in {lock_result_key}")
    else:
        logging.ingo(f"[Kross]Lock isn't acquired in {lock_result_key} which value is {result}")
    return success

def try_to_release_etcd_lock_once(etcd_agent: store.EtcdAgent, lock_key: str=None, lock_result_key: str=None) -> bool:
    client = etcd_agent.client
    if lock_key is None:
        lock_key = path.etcd_lock_path()
    if lock_result_key is None:
        lock_result_key = path.etcd_lock_result_path(client._url)
    client.transaction(
        compare=[
            client.transactions.value(lock_key) == "1",
            client.transactions.value(lock_result_key) == "1"
        ],
        success=[
            client.transactions.put(lock_key, "0"),
            client.transactions.put(lock_result_key, "0")
        ],
        failure=[]
    )
    _result, _ = etcd_agent.read(lock_result_key)
    result = _result.decode() if _result is not None else "0"
    return result == "0"

def acquire_lock_sync(etcd_agent: store.EtcdAgent, lock_key: str=None, lock_result_key: str=None):
    sync_template(
        target=True,
        kwargs={"etcd_agent": etcd_agent, "lock_key": lock_key, "lock_result_key": lock_result_key},
        process=try_to_acquire_etcd_lock_once,
        timeout=None
    )

def release_lock_sync(etcd_agent: store.EtcdAgent, lock_key: str=None, lock_result_key: str=None):
    sync_template(
        target=True,
        kwargs={"etcd_agent": etcd_agent, "lock_key": lock_key, "lock_result_key": lock_result_key},
        process=try_to_release_etcd_lock_once,
        timeout=None
    )

def write_available_sync(etcd_agent: store.EtcdAgent, intersection: int=1, timeout=20):
    time_cnt = 0
    time_cnt = 0
    while timeout is None or time_cnt < timeout:
        if etcd_agent.write("test", "test") == None:
            time.sleep(intersection)
            time_cnt += intersection
        else:
            break
    if time_cnt < timeout:
        logging.info(f"[Kross]Etcd agent is writable.")
    else:
        logging.info(f"[Kross]Fail to sync whether etcd agent is writable in the given time.")