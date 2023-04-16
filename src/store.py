import logging
import abc

import etcd3


class StoreAgent(abc.ABC):

    @abc.abstractclassmethod
    def read(self, key, prefix=False):
        pass
    
    @abc.abstractclassmethod
    def write(self, key, value):
        pass

    @abc.abstractclassmethod
    def delete(self, key, prefix=False):
        pass

class EtcdAgent(StoreAgent):
    def __init__(self, host: str=None, port: int=None, ca_cert: str=None, cert_key: str=None, cert_cert: str=None):
        super().__init__()
        
        if host is None:
            host = "127.0.0.1"
        if port is None:
            port = 2379
        self.client = etcd3.client(host=host, port=port, ca_cert=ca_cert, cert_key=cert_key, cert_cert=cert_cert)
        self.client.status() #validate accessibility

    def read(self, key: str, prefix: bool=False):
        try:
            if prefix:
                return self.client.get_prefix(prefix)
            else:
                return self.client.get(key)
        except Exception as e:
            logging.exception(f"Fail to read {key} from etcd.\n%s", e)
            return None, None
    
    def write(self, key: str, value: bytes):
        try:
            return self.client.put(key, value)
        except Exception as e:
            logging.exception(f"Fail to write {key, value} into etcd.\n%s", e)
            return None

    def delete(self, key: str, prefix:bool=False):
        try:
            return self.client.delete(key, prefix, True)
        except Exception as e:
            logging.exception(f"Fail to delete {key}(prefix={prefix}) from etcd.\n%s", e)
            return None

    def add_member(self, urls: str):
        self.client.add_member(urls)

    @property
    def members(self):
        return list(self.client.members)