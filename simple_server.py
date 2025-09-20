#!/usr/bin/env python3
"""Ultra-simple HTTP server for debugging."""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "message": "Speech-to-Phrase Validator",
                "status": "running",
                "version": "0.3.0",
                "mode": "simple_fallback"
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")

if __name__ == "__main__":
    print("Starting simple HTTP server on port 8099...")
    server = HTTPServer(('0.0.0.0', 8099), SimpleHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()