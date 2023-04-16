import item

"""
in cluster etcd
"""

def svc_path(service: item.ServiceItem=None): #records for svc in local cluster
    return f"/kross/svc/{service.name}"

def etcd_cluster_info_path(): #records for etcd pods
    return "/kross/etcd/info"

def etcd_cluster_add_member(): #url path
    return "/kross/etcd/add"