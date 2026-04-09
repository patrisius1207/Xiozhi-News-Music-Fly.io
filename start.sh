#!/bin/bash
# Jalankan HTTP keepalive di port 8080 (dibutuhkan Fly.io)
python -c "
import http.server, threading
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'XiaoZhi MCP OK')
    def log_message(self, *a): pass
httpd = http.server.HTTPServer(('0.0.0.0', 8080), H)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
print('HTTP keepalive running on :8080')
" &

# Jalankan Audio Stream Server di port 2233
# (meniru API server komunitas xiaozhi-esp32-music)
python stream_server.py &

# Jalankan MCP pipe (proses utama)
python mcp_pipe.py
