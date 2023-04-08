import logging

from kubernetes import client

from item import ServiceItem


class IngressAgent:
    def __init__(self, n_v1: client.NetworkingV1Api, ingress_class: str="nginx"):
        self.n_v1 = n_v1
        self.ingress_class = ingress_class

    def create_ingress_template(self, name: str, namespace: str="default"):
        return client.V1Ingress(
            api_version = "networking.k8s.io/v1",
            kind = "Ingress",
            metadata = client.V1ObjectMeta(
                annotations = {"kubernetes.io/ingress.class": self.ingress_class},
                name = name,
                namespace = namespace,
            ),
            spec = client.V1IngressSpec(
                rules = [
                    client.V1IngressRule(
                        http = client.V1HTTPIngressRuleValue(
                            paths = [] #Warning: the object can't exist inthe cluster because paths list is empty!
                        )
                    )
                ] 
            )
        )
    
    def insert_svc_into_ingress(self, ingress: client.V1Ingress, service: ServiceItem):
        for port_item in service.ports:
            if port_item.protocol in ["http", "https"]:
                ingress.spec.rules[0].http.paths.append(
                    client.V1HTTPIngressPath(
                        path = f"/{service.name}/{port_item.port}",
                        path_type = "Prefix",
                        backend = client.V1IngressBackend(
                            service = client.V1IngressServiceBackend(
                                name = service.name,
                                port = client.V1ServiceBackendPort(
                                    number = port_item.port
                                )
                            )
                        )
                    )
                )

    def get_ingress(self, name: str, namespace: str="default", create: bool=True):
        try:
            ingress = self.n_v1.read_namespaced_ingress(name=name, namespace=namespace)
        except client.ApiException:
            ingress = None
        return ingress

    def register_svc(self, name: str, namespace: str="default", service: ServiceItem=None):
        if service is None:
            return
        ingress = self.get_ingress(name=name, namespace=namespace)
        if ingress is None:
            body = self.create_ingress_template(name=name, namespace=namespace)
        self.insert_svc_into_ingress(body, service)
        if ingress is None:
            self.n_v1.create_namespaced_ingress(namespace=namespace, body=body)
        else:
            self.n_v1.replace_namespaced_ingress(name=name, namespace=namespace, body=body)
