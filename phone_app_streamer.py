"""
Connects to an Android phone running the free 'IP Webcam' app
and forwards the camera frames directly to the PATCHSENSE AI engine.
"""

import sys
import time
import json
import asyncio
import cv2
import websockets

DEFAULT_SERVER = "ws://127.0.0.1:8000/ws/ingest"

async def stream_ip_webcam(stream_url):
    print("=" * 65)
    print(f"[*] Connecting to Phone Camera: {stream_url}")
    print(f"[*] Forwarding to AI Server: {DEFAULT_SERVER}")
    print("=" * 65)

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"[!] Error: Could not connect to {stream_url}")
        print("[!] Make sure your phone and laptop are on the same Wi-Fi")
        print("[!] and 'IP Webcam' app server is running on your phone.")
        return

    while True:
        try:
            async with websockets.connect(DEFAULT_SERVER) as ws:
                print("[+] Connected to PATCHSENSE Server! Streaming phone camera live...\n")
                frame_count = 0
                while True:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        print("[!] Dropped frame from phone. Retrying...")
                        await asyncio.sleep(0.1)
                        continue

                    # Resize to standard detection resolution
                    resized = cv2.resize(frame, (640, 480))
                    _, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    await ws.send(jpeg.tobytes())

                    frame_count += 1
                    if frame_count % 15 == 0:
                        print(f"   [Streaming] Sent frame #{frame_count} from phone")

                    await asyncio.sleep(0.2) # ~5 FPS

        except Exception as e:
            print(f"[!] Reconnecting to server: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.1.15:8080/video"
    asyncio.run(stream_ip_webcam(url))
