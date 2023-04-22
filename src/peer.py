import json
import logging
import urllib.request

import kubernetes

import path
import store
import sync


def get_info_from_peer(host: str, port: int=38000, protocol: str="http"):
    url = f"{protocol}://{host}:{port}{path.etcd_cluster_info_path()}"
    
    info = urllib.request.urlopen(url).read().decode()
    info = json.loads(info)
    return info

def get_host_candidate(v1: kubernetes.client.CoreV1Api): #use the first ip in dictionary order
    ips = []
    for item in v1.list_node().items:
        for address in item.status.addresses:
            if address.type == "InternalIP":
                ips.append(address.address)
                break
    ips.sort()
    return ips[0]

def in_cluster(info: list, store_agent: store.StoreAgent, candidate:str):
    if info is None:
        _info, _ = store_agent.read(path.etcd_cluster_info_path())
        info = json.loads(_info) if _info is not None else []
    ret = False
    for peer in info:
        if peer["host"] == candidate:
            ret = True
            break
    logging.debug(f"[Kross]{candidate} is in cluster.")
    return ret

def create_etcd_service(v1: kubernetes.client.CoreV1Api, name: str="kross-etcd", namespace: str="default", client_node_port: int=32379, peers_node_port: int=32380):
    v1.create_namespaced_service(
        namespace=namespace,
        body=kubernetes.client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=kubernetes.client.V1ObjectMeta(
                name=name,
                labels={
                    "app": "kross-etcd",
                }
            ),
            spec=kubernetes.client.V1ServiceSpec(
                ports=[
                    kubernetes.client.V1ServicePort(
                        name="client",
                        node_port=client_node_port,
                        port=2379,
                        target_port=2379,
                        protocol="TCP",
                    ),
                    kubernetes.client.V1ServicePort(
                        name="peers",
                        node_port=peers_node_port,
                        port=2380,
                        target_port=2380,
                        protocol="TCP",
                    ),
                ],
                type="NodePort",
                selector={
                    "app": "kross-etcd",
                }
            )
        )
    )

def create_etcd_pod(v1: kubernetes.client.CoreV1Api, name: str="kross-ectd", namespace: str="default", command: str="exit"):
    v1.create_namespaced_pod(
        namespace=namespace,
        body=kubernetes.client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=kubernetes.client.V1ObjectMeta(
                name=name,
                labels={
                    "app": "kross-etcd",
                }
            ),
            spec=kubernetes.client.V1PodSpec(
                containers=[
                    kubernetes.client.V1Container(
                        image="quay.mirrors.ustc.edu.cn/coreos/etcd",
                        name="etcd",
                        ports=[
                            kubernetes.client.V1ContainerPort(
                                container_port=2379,
                            ),
                            kubernetes.client.V1ContainerPort(
                                container_port=2380
                            )
                        ],
                        command=[
                            "/bin/sh",
                            "-ecx",
                            command
                        ]
                    )
                ]
            )
        )
    )

def gen_etcd_initial_command(pod_info: dict, cluster_info: list, initial_cluster_token: str="etcd-cluster",initial_cluster_state: str="new"):
    if cluster_info is None:
        cluster_info = []
    initial_cluster = ",".join(map(lambda item: f"{item['name']}=http://{item['host']}:{item['peers_node_port']}", cluster_info))
    
    command = \
    f"exec etcd --name {pod_info['name']} \
        --listen-peer-urls http://0.0.0.0:2380 \
        --listen-client-urls http://0.0.0.0:2379 \
        --advertise-client-urls http://{pod_info['host']}:{pod_info['client_node_port']} \
        --initial-advertise-peer-urls http://{pod_info['host']}:{pod_info['peers_node_port']} \
        --initial-cluster-token {initial_cluster_token} \
        --initial-cluster {initial_cluster} \
        --initial-cluster-state {initial_cluster_state}"
    return command

def store_cluster_info(info: list, store_agent: store.StoreAgent):
    store_agent.write(path.etcd_cluster_info_path(), json.dumps(info))

def recommand_etcd_endpoints(num: int, candidate: str, base_port: int=32379):
    info = []
    for i in range(num):
        client_node_port = base_port + i * 2
        peers_node_port = client_node_port + 1
        svc_name = f"kross-etcd-{i}"
        etcd_name = f"kross-etcd-{candidate}-{i}"
        info.append({
            "name": etcd_name,
            "svc": svc_name,
            "host": candidate,
            "client_node_port": client_node_port,
            "peers_node_port": peers_node_port,
        })
    return info

def create_etcd_endpoints(v1: kubernetes.client.CoreV1Api, store_agent: store.StoreAgent, pods_info: list, info: list=None, initial_cluster_state: str="new", namespace: str="default", peer: dict=None):
    if info is None:
        info = []
    for pod_info in pods_info:
        info.append(pod_info)
        if initial_cluster_state == "existing": # needs to join the cluster first
            join_cluster(pod_info=pod_info, host=peer["host"], port=peer["port"])
            cluster_info = info
        else:
            cluster_info = pods_info
        command = gen_etcd_initial_command(pod_info=pod_info, cluster_info=cluster_info, initial_cluster_state=initial_cluster_state)
        create_etcd_service(v1=v1, name=pod_info["svc"], client_node_port=pod_info["client_node_port"], peers_node_port=pod_info["peers_node_port"], namespace=namespace)
        create_etcd_pod(v1=v1, name=pod_info["name"], command=command, namespace=namespace)
        sync.pod_running_sync(v1=v1, name=pod_info["name"], namespace=namespace)
    store_cluster_info(info=info, store_agent=store_agent)

def join_cluster(pod_info: dict, host: str, port: int=38000, protocol: str="http"):
    url = f"{protocol}://{host}:{port}{path.etcd_cluster_add_member_path()}"
    data = json.dumps(pod_info).encode()
    headers = {'Content-type': 'application/json', 'Content-Length': len(data)}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    urllib.request.urlopen(req)


def handle_peers(v1: kubernetes.client.CoreV1Api, store_agent: store.StoreAgent, peers: list=None, base_port: int=32379, namespace: str="default") -> store.StoreAgent:
    candidate = get_host_candidate(v1=v1)
    if peers is None or len(peers) == 0:
        if not in_cluster(info=None, store_agent=store_agent, candidate=candidate):
            pods_info = recommand_etcd_endpoints(3, candidate=candidate, base_port=base_port)
            create_etcd_endpoints(v1=v1, store_agent=store_agent, pods_info=pods_info, info=None, initial_cluster_state="new", namespace=namespace)
    else:
        peer = peers[0] #todo, only use the first one now
        info = get_info_from_peer(**peer)
        if not in_cluster(info=info, store_agent=store_agent, candidate=candidate):
            pods_info = recommand_etcd_endpoints(2, candidate=candidate, base_port=base_port)
            create_etcd_endpoints(v1=v1, store_agent=store_agent, pods_info=pods_info, info=info, initial_cluster_state="existing", namespace=namespace, peer=peer)
    
    _local_info, _ = store_agent.read(path.etcd_cluster_info_path())
    local_info = json.loads(_local_info) if _local_info is not None else []
    for pod_info in local_info:
        if pod_info["host"] == candidate:
            kross_ectd_agent = store.EtcdAgent(host=pod_info["host"], port=pod_info["client_node_port"])
            return kross_ectd_agent #normal return value
    logging.error(f"[Kross]local etcd doesn't store info about kross etcd pod in this cluster!")
    return None
