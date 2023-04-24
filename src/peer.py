import json
import logging
import urllib.request

import kubernetes

import path
import store
import sync


def acquire_lock_by_peer(lock_result_key : str, host: str, port: int=30789, protocol: str="http"):
    url = f"{protocol}://{host}:{port}{path.etcd_acquire_lock_path()}"
    data = json.dumps({
        "lock_result_key": lock_result_key
    }).encode()
    headers = {'Content-type': 'application/json', 'Content-Length': len(data)}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    sync.sync_template(
        target="ok",
        kwargs={"url": req},
        process=lambda kwargs: urllib.request.urlopen(**kwargs).read().decode(),
        intersection=1,
        timeout=None
    )

def release_lock_by_peer(lock_result_key: str, host: str, port: int=30789, protocol: str="http"):
    url = f"{protocol}://{host}:{port}{path.etcd_release_lock_path()}"
    data = json.dumps({
        "lock_result_key": lock_result_key
    }).encode()
    headers = {'Content-type': 'application/json', 'Content-Length': len(data)}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    sync.sync_template(
        target="ok",
        kwargs={"url": req},
        process=lambda kwargs: urllib.request.urlopen(**kwargs).read().decode(),
        intersection=1,
        timeout=None
    )

def get_info_from_peer(host: str, port: int=30789, protocol: str="http"):
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

def get_true_server_port(v1: kubernetes.client.CoreV1Api, server_port: int=7890, namespace: str="default"): #find the node port kross server uses
    try: #in k8s
        kross_svc = v1.read_namespaced_service(name="kross-svc", namespace=namespace)
        return kross_svc.spec.ports[0].node_port
    except Exception:
        return server_port

def in_cluster(info: list, local_etcd_agent: store.EtcdAgent, candidate:str):
    if info is None:
        _info, _ = local_etcd_agent.read(path.etcd_cluster_info_path())
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

def recommand_etcd_endpoints(num: int, candidate: str, base_port: int=32379, server_port: int=7890):
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
            "server_port": server_port,
        })
    return info

def get_kross_etcd_agent_from_info(host: str, info: list):
    for pod_info in info:
        if pod_info["host"] == host:
            kross_ectd_agent = store.EtcdAgent(host=pod_info["host"], port=pod_info["client_node_port"])
            return kross_ectd_agent

def create_etcd_endpoints(v1: kubernetes.client.CoreV1Api, local_etcd_agent: store.EtcdAgent, pods_info: list, lock_result_key: str, info: list=None, initial_cluster_state: str="new", namespace: str="default", peer: dict=None):
    if info is None:
        info = []
    for pod_info in pods_info:
        info.append(pod_info)
        if initial_cluster_state == "existing": # needs to join the cluster first
            join_cluster(lock_result_key=lock_result_key, pod_info=pod_info, host=peer["host"], port=peer["port"])
            cluster_info = info
        else:
            cluster_info = pods_info
        command = gen_etcd_initial_command(pod_info=pod_info, cluster_info=cluster_info, initial_cluster_state=initial_cluster_state)
        create_etcd_service(v1=v1, name=pod_info["svc"], client_node_port=pod_info["client_node_port"], peers_node_port=pod_info["peers_node_port"], namespace=namespace)
        create_etcd_pod(v1=v1, name=pod_info["name"], command=command, namespace=namespace)
        sync.pod_running_sync(v1=v1, name=pod_info["name"], namespace=namespace)
    store_cluster_info(info=info, store_agent=local_etcd_agent)
    kross_etcd_agent = get_kross_etcd_agent_from_info(host=pods_info[0]["host"], info=info)
    store_cluster_info(info=info, store_agent=kross_etcd_agent)
    return kross_etcd_agent

def join_cluster(lock_result_key: str, pod_info: dict, host: str, port: int=30789, protocol: str="http"):
    url = f"{protocol}://{host}:{port}{path.etcd_cluster_add_member_path()}"
    data = json.dumps({
        "pod_info": pod_info,
        "lock_result_key": lock_result_key
    }).encode()
    headers = {'Content-type': 'application/json', 'Content-Length': len(data)}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    sync.sync_template(
        target="ok",
        kwargs={"url": req},
        process=lambda kwargs: urllib.request.urlopen(**kwargs).read().decode(),
        intersection=1,
        timeout=None
    )

def handle_peers(v1: kubernetes.client.CoreV1Api, local_etcd_agent: store.EtcdAgent, peers: list=None, base_port: int=32379, namespace: str="default", server_port: int=7890) -> store.StoreAgent:
    global candidate
    global lock_result_key
    candidate = get_host_candidate(v1=v1)
    lock_result_key = path.etcd_lock_result_path(candidate)
    server_port = get_true_server_port(v1=v1, server_port=server_port, namespace=namespace)
    if peers is None or len(peers) == 0:
        if not in_cluster(info=None, local_etcd_agent=local_etcd_agent, candidate=candidate):
            pods_info = recommand_etcd_endpoints(3, candidate=candidate, base_port=base_port, server_port=server_port)
            kross_etcd_agent = create_etcd_endpoints(v1=v1, local_etcd_agent=local_etcd_agent, pods_info=pods_info, lock_result_key=lock_result_key, info=None, initial_cluster_state="new", namespace=namespace)
            sync.init_etcd_lock(etcd_agent=kross_etcd_agent)
    else:
        peer = peers[0] #only use the first one, maybe can be improved by select the best peer
        acquire_lock_by_peer(lock_result_key=lock_result_key, **peer)
        info = get_info_from_peer(**peer)
        if not in_cluster(info=info, local_etcd_agent=local_etcd_agent, candidate=candidate):
            pods_info = recommand_etcd_endpoints(2, candidate=candidate, base_port=base_port, server_port=server_port)
            kross_etcd_agent = create_etcd_endpoints(v1=v1, local_etcd_agent=local_etcd_agent, pods_info=pods_info, lock_result_key=lock_result_key, info=info, initial_cluster_state="existing", namespace=namespace, peer=peer)

    _local_info, _ = local_etcd_agent.read(path.etcd_cluster_info_path())
    local_info = json.loads(_local_info) if _local_info is not None else []
    kross_etcd_agent = get_kross_etcd_agent_from_info(host=candidate, info=local_info)
    if kross_etcd_agent is None:
        logging.error(f"[Kross]local etcd doesn't store info about kross etcd pod in this cluster!")
    sync.release_lock_sync(etcd_agent=kross_etcd_agent, lock_result_key=lock_result_key) #release the lock if it holds
    return kross_etcd_agent

def quit_peers(kross_etcd_agent: store.EtcdAgent):
    sync.acquire_lock_sync(etcd_agent=kross_etcd_agent, lock_result_key=lock_result_key)
    _info, _ = kross_etcd_agent.read(path.etcd_cluster_info_path())
    info = json.loads(_info)
    peerurls_to_remove = list(map(lambda pod_info: f"http://{pod_info['host']}:{pod_info['peers_node_port']}", filter(lambda pod_info: pod_info["host"] == candidate, info)))
    new_info = list(filter(lambda pod_info: pod_info["host"] != candidate, info))
    if len(new_info):
        peer_info = new_info[0]
        kross_etcd_agent.write(path.etcd_cluster_info_path(), json.dumps(new_info))
        members_to_remove = list(filter(lambda member: member.peer_urls[0] in peerurls_to_remove, kross_etcd_agent.members)) #warning: one peerurl for one member here
        for i in range(len(members_to_remove)):
            if f"http://{kross_etcd_agent.client._url}" in members_to_remove[i].peer_urls:
                members_to_remove[-1], members_to_remove[i] = members_to_remove[i], members_to_remove[-1]
                break
        for member in members_to_remove:
            member.remove()
        release_lock_by_peer(lock_result_key=lock_result_key, host=peer_info["host"], port=peer_info["server_port"])
    else:
        pass