import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer

import path
import store


class KrossRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, store_agent: store.StoreAgent, *args, **kwargs):
        self.store_agent =  store_agent
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == path.etcd_cluster_info_path():
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            _message, _ = self.store_agent.read(path.etcd_cluster_info_path())
            self.wfile.write(_message)
            return
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "404"
            self.wfile.write(bytes(message, "utf8"))
            return

def start_server(store_agent: store.StoreAgent, port: int=8000):
    def new_handler(*args, **kwargs):
        KrossRequestHandler(store_agent, *args, **kwargs)
    server = HTTPServer(('', port), new_handler)
    server.serve_forever()
