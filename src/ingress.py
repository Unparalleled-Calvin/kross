from kubernetes.client import NetworkingV1Api

class IngressAgent: #存储name_space+name的Ingress信息
    def __init__(self, n_v1: NetworkingV1Api, ingress_class: str="nginx"):
        self.n_v1 = n_v1
