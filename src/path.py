import item

"""
in cluster etcd
"""

def svc_path(service: str, host: str): #for etcd, records for svc
    if host is None:
        return f"/kross/svc/{service}"
    return f"/kross/svc/{service}/{host}" #for etcd

def svc_info_path(): #for server
    return "/kross/svc"

def etcd_cluster_info_path(): #for server and etcd, records for etcd pods
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