"""Simple HTTPS server with a self-signed certificate for local development."""
import http.server
import ssl
import os
import subprocess
import sys

PORT = 8443
CERT_FILE = os.path.join(os.path.dirname(__file__), '_dev_cert.pem')
KEY_FILE  = os.path.join(os.path.dirname(__file__), '_dev_key.pem')

# Generate self-signed cert if not present
if not os.path.exists(CERT_FILE):
    print("Generating self-signed certificate...")
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
        '-keyout', KEY_FILE, '-out', CERT_FILE,
        '-days', '365', '-nodes',
        '-subj', '/CN=localhost'
    ], check=True)
    print("Certificate generated.")

os.chdir(os.path.dirname(__file__) or '.')

handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.HTTPServer(('0.0.0.0', PORT), handler)

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(CERT_FILE, KEY_FILE)
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

# Get local IP
import socket
hostname = socket.gethostname()
try:
    local_ip = socket.gethostbyname(hostname)
except:
    local_ip = '127.0.0.1'

print(f"\nHTTPS server running:")
print(f"  Local:   https://localhost:{PORT}")
print(f"  Network: https://{local_ip}:{PORT}")
print(f"\nOn your phone, open: https://{local_ip}:{PORT}/ar-flashcards/mobile.html")
print("NOTE: Browser will warn about the certificate — tap 'Advanced' → 'Proceed' to continue.\n")
httpd.serve_forever()
