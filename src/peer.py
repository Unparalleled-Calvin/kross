import json
import logging

from kubernetes import client

from path import etcd_cluster_info_path
from store import StoreAgent


def get_info_from_peer(host, port):
    pass

def get_host_candidate(v1: client.CoreV1Api): #use the first ip in dictionary order
    ips = []
    for item in v1.list_node().items:
        for address in item.status.addresses:
            if address.type == "InternalIP":
                ips.append(address.address)
                break
    ips.sort()
    return ips[0]

def in_cluster(info: list, store_agent: StoreAgent, candidate:str):
    if info is None:
        _info, _ = store_agent.read(etcd_cluster_info_path())
        info = json.loads(_info) if _info is not None else []
    ret = False
    for peer in info:
        if peer["host"] == candidate:
            ret = True
            break
    logging.debug(f"{candidate} is in cluster.")
    return ret

def create_etcd_service(v1: client.CoreV1Api, name: str="kross-etcd", namespace: str="default", client_node_port: int=32379, peers_node_port: int=32380):
    v1.create_namespaced_service(
        namespace=namespace,
        body=client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=name,
                labels={
                    "app": "kross-etcd",
                }
            ),
            spec=client.V1ServiceSpec(
                ports=[
                    client.V1ServicePort(
                        name="client",
                        node_port=client_node_port,
                        port=2379,
                        target_port=2379,
                        protocol="TCP",
                    ),
                    client.V1ServicePort(
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

def create_etcd_pod(v1: client.CoreV1Api, name: str="kross-ectd", namespace: str="default", command: str="exit"):
    v1.create_namespaced_pod(
        namespace=namespace,
        body=client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=client.V1ObjectMeta(
                name=name,
                labels={
                    "app": "kross-etcd",
                }
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        image="quay.mirrors.ustc.edu.cn/coreos/etcd",
                        name="etcd",
                        ports=[
                            client.V1ContainerPort(
                                container_port=2379,
                            ),
                            client.V1ContainerPort(
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

def store_cluster_info(info: list, store_agent: StoreAgent):
    store_agent.write(etcd_cluster_info_path(), json.dumps(info))

def create_etcd_endpoints(v1: client.CoreV1Api, store_agent: StoreAgent, candidate: str, num: int=1, info: list=None, initial_cluster_state: str="new"):
    if info is None:
        info = []
    for i in range(num):
        client_node_port = 32379 + i * 2
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
    for i in range(-num, 0):
        pod_info = info[i]
        command = gen_etcd_initial_command(pod_info=pod_info, cluster_info=info, initial_cluster_state=initial_cluster_state)
        create_etcd_service(v1=v1, name=pod_info["svc"], client_node_port=pod_info["client_node_port"], peers_node_port=pod_info["peers_node_port"])
        create_etcd_pod(v1=v1, name=pod_info["name"], command=command)
    store_cluster_info(info=info, store_agent=store_agent)

def join_cluster():
    pass

def handle_peers(v1: client.CoreV1Api, store_agent: StoreAgent, peers: list=None):
    candidate = get_host_candidate(v1=v1)
    if peers is None or len(peers) == 0:
        if not in_cluster(info=None, store_agent=store_agent, candidate=candidate):
            create_etcd_endpoints(v1=v1, candidate=candidate, num=2, store_agent=store_agent, info=None, initial_cluster_state="new")
    # else:
    #     peer = peers[0] #todo, only use the first one
    #     info = get_info_from_peer(**peer)
    #     if not in_cluster(info=info, store_agent=store_agent, candidate=candidate):
    #         create_etcd_endpoints(v1=v1, candidate=candidate, num=2, store_agent=store_agent, info=info)
    #         join_cluster()
