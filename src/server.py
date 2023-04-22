import http.server
import json
import logging
import time

import etcd3

import path
import store
import sync


class KrossRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, local_etcd_agent: store.EtcdAgent, kross_etcd_agent: store.EtcdAgent, *args, **kwargs):
        self.local_etcd_agent = local_etcd_agent
        self.kross_etcd_agent = kross_etcd_agent
        super().__init__(*args, **kwargs)

    def reply(self, message: bytes):
        message = bytes(message, "utf8")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(message)

    def do_GET(self):
        if self.path == path.etcd_cluster_info_path():
            _message, _ = self.local_etcd_agent.read(path.etcd_cluster_info_path())
            self.reply(_message)
        if self.path == path.shutdown_path():
            self.reply("ok, the server will shutdown.")
            raise ShutdownException("the server received a shutdown request")
        else:
            self.reply("404")
    
    def do_POST(self):
        if self.path == path.etcd_cluster_add_member_path():
            length = int(self.headers['content-length'])  # 获取除头部后的请求参数的长度
            data = self.rfile.read(length)
            pod_info = json.loads(data.decode())
            peerUrls = [f"http://{pod_info['host']}:{pod_info['peers_node_port']}"]
            if sync.acquire_etcd_lock(etcd_agent=self.kross_etcd_agent):
                sync.etcd_member_added_sync(etcd_agent=self.kross_etcd_agent, peerUrls=peerUrls)
                sync.release_etcd_lock(etcd_agent=self.kross_etcd_agent)
                self.reply("ok")
            else:
                self.reply("fail")
        else:
            self.reply("404")

class ShutdownException(Exception):
    def __init__(self, reason):
        super().__init__()
        self.reason = reason

    def __str__(self):
        return f"The server shutdown because {self.reason}"

def start_server(local_etcd_agent: store.EtcdAgent, kross_etcd_agent: store.EtcdAgent, port: int=7890):
    def new_handler(*args, **kwargs):
        KrossRequestHandler(local_etcd_agent, kross_etcd_agent, *args, **kwargs)
    server = http.server.HTTPServer(('', port), new_handler)
    try:
        server.serve_forever()
    except ShutdownException as e:
        server.shutdown()
        logging.info(e)