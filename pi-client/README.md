# PATCHSENSE Pi Client (Raspberry Pi Zero 2 W)

This script captures video frames from a camera attached to the Raspberry Pi Zero 2 W and streams raw binary JPEG frames over WebSocket to the laptop inference server.

## Features
- **Picamera2** native support for Raspberry Pi OS (Bookworm), with fallback to OpenCV `cv2.VideoCapture(0)` or synthetic frame generator.
- **Binary WebSocket Streaming** for low latency and minimal bandwidth on mobile hotspots.
- **Configurable Server Address**: Easily update `config.json` when your laptop's Wi-Fi hotspot IP address changes.
- **Offline Buffering Queue**: Saves frames locally to `./offline_queue` if Wi-Fi connection drops, auto-draining once reconnected.

## Setup Instructions on Raspberry Pi
1. Clone this directory onto your Pi:
   ```bash
   git clone <repo-url>
   cd pi-client
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Update `config.json` with your laptop's current Wi-Fi IP address:
   ```json
   {
     "server_url": "ws://192.168.1.100:8000/ws/ingest",
     "fps": 3,
     "jpeg_quality": 75
   }
   ```

4. Run the streamer:
   ```bash
   python main.py
   ```
   Or pass server URL directly:
   ```bash
   python main.py --server ws://192.168.43.12:8000/ws/ingest
   ```
