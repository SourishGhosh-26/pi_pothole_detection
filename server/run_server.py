import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import asyncio
import uvicorn

# Ensure server dir is in sys.path
server_dir = os.path.dirname(os.path.abspath(__file__))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from main import app

async def run_both():
    cert_file = os.path.join(server_dir, "cert.pem")
    key_file = os.path.join(server_dir, "key.pem")

    # 1. HTTP Server on port 8000 (For Laptop Dashboard & standard access)
    config_http = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server_http = uvicorn.Server(config_http)
    tasks = [server_http.serve()]

    # 2. HTTPS Server on port 8443 (For Mobile Phone Real Camera & GPS access)
    if os.path.exists(cert_file) and os.path.exists(key_file):
        config_https = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8443,
            ssl_keyfile=key_file,
            ssl_certfile=cert_file,
            log_level="warning"
        )
        server_https = uvicorn.Server(config_https)
        tasks.append(server_https.serve())
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            lan_ip = s.getsockname()[0]
        except Exception:
            lan_ip = '127.0.0.1'
        finally:
            s.close()

        print("=" * 68)
        print(f" [*] LAPTOP DASHBOARD (HTTP):      http://localhost:8000/")
        print(f" [*] PHONE REAL CAMERA (HTTPS):    https://{lan_ip}:8443/camera")
        print(f" [*] PHONE DASHBOARD (HTTP):       http://{lan_ip}:8000/")
        print("=" * 68)

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_both())
