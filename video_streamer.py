"""
PATCHSENSE — Road Video & Telemetry Streamer for Presentations
Streams video frames (from a file, YouTube download, or synthetic generator)
along with simulated vehicle GPS movement to the FastAPI server.
"""

import os
import sys
import time
import json
import math
import argparse
import asyncio
import numpy as np
import cv2
import websockets

# Ensure clean UTF-8 output on Windows cmd/powershell
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

DEFAULT_SERVER = "ws://127.0.0.1:8000"
INGEST_URL = f"{DEFAULT_SERVER}/ws/ingest"
GPS_URL = f"{DEFAULT_SERVER}/ws/gps"

# Simulated Road Coordinates (Route through Kolkata EM Bypass / Central corridor)
ROUTE_WAYPOINTS_BUS101 = [
    (22.5726, 88.3639),  # Starting point: Esplanade / Central Kolkata
    (22.5645, 88.3712),  # Sealdah Flyover Approach
    (22.5448, 88.3685),  # Park Circus 7-Point
    (22.5390, 88.3965),  # Science City / EM Bypass Arterial
    (22.5180, 88.3980),  # Ruby Hospital Crossing
    (22.4985, 88.3995)   # Kalikapur / Garia Corridor
]

# Simulated Road Coordinates for BUS-104 (VIP Road & Salt Lake Sector V Corridor)
ROUTE_WAYPOINTS_BUS104 = [
    (22.5980, 88.3950),  # Ultadanga Crossing / VIP Road Entry
    (22.5890, 88.4050),  # Lake Town VIP Road Bottleneck
    (22.5820, 88.4160),  # Salt Lake Gate / Bypass
    (22.5710, 88.4280),  # Karunamoyee Central
    (22.5620, 88.4350)   # Sector V Tech Hub Terminal
]

ROUTE_WAYPOINTS = ROUTE_WAYPOINTS_BUS101

def generate_synthetic_road_frame(frame_num: int, width: int = 640, height: int = 480) -> np.ndarray:
    """Generates an authentic asphalt road perspective frame with moving lane markings."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Asphalt gradient (darker near horizon, textured closer)
    for y in range(height):
        ratio = y / height
        val = int(45 + ratio * 25)
        frame[y, :] = (val, val, val)
    
    # Add asphalt aggregate noise
    noise = np.random.randint(-8, 8, (height, width, 3), dtype=np.int16)
    frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Perspective road lanes (vanishing point at center horizon)
    vx, vy = width // 2, height // 3
    cv2.line(frame, (vx, vy), (40, height), (180, 180, 180), 3)       # Left road edge
    cv2.line(frame, (vx, vy), (width - 40, height), (180, 180, 180), 3) # Right road edge
    
    # Dashed center line with perspective animation
    speed = 14
    offset = (frame_num * speed) % 80
    for y in range(vy + offset, height, 80):
        scale = (y - vy) / float(height - vy)
        line_len = int(25 * scale)
        line_w = max(2, int(6 * scale))
        x = vx
        cv2.line(frame, (x, y), (x, min(height, y + line_len)), (250, 250, 250), line_w)
    
    # Draw simulated pothole every ~60 frames
    cycle = frame_num % 120
    if 30 <= cycle <= 80:
        p_progress = (cycle - 30) / 50.0  # 0.0 to 1.0 (approaching)
        py = int(vy + p_progress * (height - vy - 40))
        px = int(vx - 60 * p_progress)
        pw = max(10, int(90 * p_progress))
        ph = max(6, int(45 * p_progress))
        
        # Draw dark crater with rough jagged outline
        cv2.ellipse(frame, (px, py), (pw // 2, ph // 2), 0, 0, 360, (20, 20, 20), -1)
        cv2.ellipse(frame, (px, py), (pw // 2, ph // 2), 0, 0, 360, (15, 15, 15), 2)
        # Internal broken asphalt texture
        cv2.ellipse(frame, (px + 4, py + 2), (pw // 3, ph // 3), -10, 0, 360, (10, 10, 10), -1)

    return frame

async def run_stream(bus_id: str = "BUS-101", video_path: str = None, fps: int = 5):
    print("=" * 65)
    print(" [*] PATCHSENSE ROAD VIDEO & TELEMETRY STREAMER")
    print("=" * 65)
    print(f"[*] Assigned Public Transit Vehicle: {bus_id}")

    waypoints = ROUTE_WAYPOINTS_BUS104 if bus_id == "BUS-104" else ROUTE_WAYPOINTS_BUS101

    if not video_path:
        if bus_id == "BUS-104":
            vid_candidates = [
                os.path.join("server", "static", "bus104_traffic.mp4"),
                "bus104_traffic.mp4"
            ]
        else:
            vid_candidates = [
                os.path.join("server", "static", "youtube_demo.mp4"),
                os.path.join(os.path.dirname(__file__), "real_road_demo.mp4"),
                "real_road_demo.mp4"
            ]
        for c in vid_candidates:
            if os.path.exists(c):
                video_path = c
                break

    if video_path and os.path.exists(video_path):
        print(f"[*] Mode: Video Stream ({os.path.basename(video_path)})")
    else:
        print("[*] Mode: Synthetic Road Generator (Realistic moving road + defects)")
        video_path = None
    print(f"[*] Target Server: {DEFAULT_SERVER}")
    print(f"[*] Frame Rate: {fps} FPS")
    print("=" * 65)

    cap = None
    if video_path:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[!] Warning: Could not open {video_path}. Falling back to road generator.")
            cap = None

    frame_interval = 1.0 / fps
    frame_num = 0

    # Continuous reconnect loop
    while True:
        try:
            print(f"[*] Connecting to {INGEST_URL} and {GPS_URL}...")
            async with websockets.connect(INGEST_URL) as ws_ingest, \
                       websockets.connect(GPS_URL) as ws_gps:
                print(f"[+] Connected to PATCHSENSE Server! Streaming live road video for {bus_id}...\n")

                # Send initial bus identity metadata
                await ws_ingest.send(json.dumps({
                    "bus_id": bus_id,
                    "camera_angle": "front",
                    "timestamp": time.time()
                }))

                while True:
                    start_time = time.time()
                    
                    # 1. Capture/Generate Frame
                    frame = None
                    if cap is not None:
                        ret, raw_frame = cap.read()
                        if not ret:
                            # Loop video back to beginning
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, raw_frame = cap.read()
                        if ret and raw_frame is not None:
                            frame = cv2.resize(raw_frame, (640, 480))
                    
                    if frame is None:
                        frame = generate_synthetic_road_frame(frame_num)

                    # Encode to JPEG
                    _, jpeg_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    jpeg_bytes = jpeg_buf.tobytes()

                    # 2. Compute Simulated GPS Position along assigned road
                    route_idx = (frame_num // 80) % (len(waypoints) - 1)
                    sub_prog = (frame_num % 80) / 80.0
                    p1 = waypoints[route_idx]
                    p2 = waypoints[route_idx + 1]
                    cur_lat = p1[0] + (p2[0] - p1[0]) * sub_prog
                    cur_lon = p1[1] + (p2[1] - p1[1]) * sub_prog

                    # 3. Transmit GPS
                    gps_payload = json.dumps({
                        "bus_id": bus_id,
                        "lat": cur_lat,
                        "lon": cur_lon,
                        "timestamp": time.time()
                    })
                    await ws_gps.send(gps_payload)

                    # 4. Transmit Frame
                    await ws_ingest.send(jpeg_bytes)

                    frame_num += 1
                    if frame_num % (fps * 2) == 0:
                        print(f"   [{bus_id} Stream Active] Sent frame #{frame_num} | Vehicle GPS: ({cur_lat:.5f}, {cur_lon:.5f})")

                    # Maintain target FPS
                    elapsed = time.time() - start_time
                    delay = max(0.01, frame_interval - elapsed)
                    await asyncio.sleep(delay)

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"[!] Connection dropped ({e}). Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[!] Stream error: {e}")
            await asyncio.sleep(3)

def main():
    parser = argparse.ArgumentParser(description="PATCHSENSE Road Video & Telemetry Streamer")
    parser.add_argument("--bus", type=str, default="BUS-101", choices=["BUS-101", "BUS-104", "BUS-208"], help="Fleet bus identifier (default: BUS-101)")
    parser.add_argument("--video", type=str, default=None, help="Path to road video file (.mp4)")
    parser.add_argument("--fps", type=int, default=5, help="Streaming FPS (default: 5)")
    args = parser.parse_args()

    asyncio.run(run_stream(bus_id=args.bus, video_path=args.video, fps=args.fps))

if __name__ == "__main__":
    main()
