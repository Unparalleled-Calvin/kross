import socketserver
from http.server import SimpleHTTPRequestHandler

PORT = 8000

class MyHttpRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/a':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = ""
            self.wfile.write(bytes(message, "utf8"))
            return
        else:
            SimpleHTTPRequestHandler.do_GET(self)

Handler = MyHttpRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()