import etcd3


class EtcdAgent:
    def __init__(self, host: str=None, port: int=None, ca_cert: str=None, cert_key: str=None, cert_cert: str=None):
        if host is None:
            host = "127.0.0.1"
        if port is None:
            port = "2379"
        self.client = etcd3.client(host=host, port=port, ca_cert=ca_cert, cert_key=cert_key, cert_cert=cert_cert)
        self.client.status() #validate accessibility