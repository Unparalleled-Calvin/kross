import kubernetes

import path
import store
import sync


def delete_kross_ectd_pod(v1: kubernetes.client.CoreV1Api, namespace: str="default"):
    v1.delete_collection_namespaced_pod(
        namespace=namespace,
        label_selector="app=kross-etcd",
        body=kubernetes.client.V1DeleteOptions()
    )
    sync.resource_deleted_sync(v1=v1, resource="pod", label_selector="app=kross-etcd", namespace=namespace)

def delete_kross_ectd_svc(v1: kubernetes.client.CoreV1Api, namespace: str="default"):
    v1.delete_collection_namespaced_service(
        namespace=namespace,
        label_selector="app=kross-etcd",
        body=kubernetes.client.V1DeleteOptions()
    )
    sync.resource_deleted_sync(v1=v1, resource="service", label_selector="app=kross-etcd", namespace=namespace)

def delete_kross_etcd_cluster_info(store_agent: store.StoreAgent):
    store_agent.delete(path.etcd_cluster_info_path())

def sanitize(v1: kubernetes.client.CoreV1Api, store_agent: store.StoreAgent, namespace: str="default"):
    delete_kross_ectd_svc(v1=v1, namespace=namespace)
    delete_kross_ectd_pod(v1=v1, namespace=namespace)
    delete_kross_etcd_cluster_info(store_agent=store_agent)
