import item

"""
in cluster etcd
"""

def svc_path(service: item.ServiceItem=None): #for etcd, records for svc in local cluster
    return f"/kross/svc/{service.name}"

def etcd_cluster_info_path(): #for server adn etcd, records for etcd pods
    return "/kross/etcd/info"

def etcd_cluster_add_member_path(): #for server, url path
    return "/kross/etcd/add"

def etcd_lock_path(): #for etcd, lock
    return "/kross/etcd/lock"

def etcd_lock_result_path(key: str): #for etcd, lock result
    return f"/kross/etcd/lock/{key}"

def etcd_acquire_lock_path(): #for server, acquire lock
    return "/kross/etcd/lock/acquire"

def etcd_release_lock_path(): #for server, release lock
    return "/kross/etcd/lock/release"

def shutdown_path(): #for server, shutdown the server
    return "/kross/server/shutdown"