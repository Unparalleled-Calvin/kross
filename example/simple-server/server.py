import http.server
import socketserver

PORT = 8000

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/a':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "a"
            self.wfile.write(bytes(message, "utf8"))
            return
        elif self.path == '/b':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            message = "b"
            self.wfile.write(bytes(message, "utf8"))
            return
        else:
            http.server.SimpleHTTPRequestHandler.do_GET(self)

Handler = MyHttpRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()