import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import etcd3

import path
import store
import util


class KrossRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, local_etcd_agent: store.EtcdAgent, kross_etcd_agent: store.EtcdAgent, *args, **kwargs):
        self.local_etcd_agent = local_etcd_agent
        self.kross_etcd_agent = kross_etcd_agent
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == path.etcd_cluster_info_path():
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            _message, _ = self.local_etcd_agent.read(path.etcd_cluster_info_path())
            self.wfile.write(_message)
            return
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "404"
            self.wfile.write(bytes(message, "utf8"))
            return
    
    def do_POST(self):
        if self.path == path.etcd_cluster_add_member():
            length = int(self.headers['content-length'])  # 获取除头部后的请求参数的长度
            data = self.rfile.read(length)
            pod_info = json.loads(data.decode())
            peerUrls = [f"http://{pod_info['host']}:{pod_info['peers_node_port']}"]
            member_num = len(self.kross_etcd_agent.members) #use atomic?
            while True:
                try:
                    self.kross_etcd_agent.add_member(peerUrls) #actually the pod hasn't been running
                except etcd3.exceptions.ConnectionFailedError as e:
                    print("waiting...")
                    time.sleep(0.5)
                else:
                    break
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "Post received"
            self.wfile.write(bytes(message, "utf8"))

def start_server(local_etcd_agent: store.EtcdAgent, kross_etcd_agent: store.EtcdAgent, port: int=8000):
    def new_handler(*args, **kwargs):
        KrossRequestHandler(local_etcd_agent, kross_etcd_agent, *args, **kwargs)
    server = HTTPServer(('', port), new_handler)
    server.serve_forever()