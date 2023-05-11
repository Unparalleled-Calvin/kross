import http.server
import json
import logging
import pathlib
import threading

import path
import store
import sync


class KrossRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, local_etcd_agent: store.EtcdAgent, kross_etcd_agent: store.EtcdAgent, *args, **kwargs):
        self.local_etcd_agent = local_etcd_agent
        self.kross_etcd_agent = kross_etcd_agent
        super().__init__(*args, **kwargs)

    def reply(self, message: bytes):
        if isinstance(message, str):
            message = bytes(message, "utf8")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(message)

    def do_GET(self):
        if self.path == path.etcd_cluster_info_path():
            _message, _ = self.local_etcd_agent.read(path.etcd_cluster_info_path())
            self.reply(_message)
        elif self.path == path.shutdown_path():
            self.reply("ok, the server will shutdown.")
            threading.Thread(target=self.server.shutdown).start()
        elif self.path.startswith(path.svc_info_path()):
            data = {}
            for value, metadata in self.kross_etcd_agent.read(self.path, prefix=True):
                key = metadata.key.decode()
                host = pathlib.Path(key).name
                value = json.loads(value)
                data[host] = value
            self.reply(json.dumps(data))
        else:
            self.reply("404")
    
    def do_POST(self):
        if self.path == path.etcd_cluster_add_member_path():
            length = int(self.headers['content-length'])
            data = self.rfile.read(length).decode()
            data = json.loads(data)
            pod_info, lock_result_key = data["pod_info"], data["lock_result_key"]
            peerUrls = [f"http://{pod_info['host']}:{pod_info['peers_node_port']}"]
            if sync.try_to_acquire_etcd_lock_once(etcd_agent=self.kross_etcd_agent, lock_result_key=lock_result_key):
                sync.etcd_member_added_sync(etcd_agent=self.kross_etcd_agent, peerUrls=peerUrls) # warning: may takes a lot of time
                self.reply("ok")
            else:
                self.reply("fail")
        elif self.path == path.etcd_acquire_lock_path():
            length = int(self.headers['content-length'])
            data = self.rfile.read(length)
            lock_result_key = json.loads(data.decode())["lock_result_key"]
            result = sync.try_to_acquire_etcd_lock_once(etcd_agent=self.kross_etcd_agent, lock_result_key=lock_result_key)
            self.reply("ok" if result else "fail")
        elif self.path == path.etcd_release_lock_path():
            length = int(self.headers['content-length'])
            data = self.rfile.read(length)
            lock_result_key = json.loads(data.decode())["lock_result_key"]
            result = sync.try_to_release_etcd_lock_once(etcd_agent=self.kross_etcd_agent, lock_result_key=lock_result_key)
            self.reply("ok" if result else "fail")
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
    server.serve_forever()
    logging.info("[Kross]Kross server has been stopped.")