import os
import sys
import json
import time
import uuid
import glob
import asyncio
import argparse
import numpy as np

try:
    import websockets
except ImportError:
    print("[ERROR] 'websockets' package missing. Run: pip install websockets")
    sys.exit(1)

# Check for Picamera2 (Raspberry Pi Zero 2 W native) and OpenCV
USE_PICAM2 = False
USE_CV2 = False

try:
    from picamera2 import Picamera2
    USE_PICAM2 = True
    print("[Pi Client] Picamera2 framework detected!")
except ImportError:
    try:
        import cv2
        USE_CV2 = True
        print("[Pi Client] OpenCV detected! (Using cv2 VideoCapture fallback)")
    except ImportError:
        print("[Pi Client] Neither Picamera2 nor OpenCV found. Using synthetic frame generator mode.")

class CameraCapture:
    def __init__(self, width=640, height=480, jpeg_quality=75):
        self.width = width
        self.height = height
        self.quality = jpeg_quality
        self.picam2 = None
        self.cap = None

        if USE_PICAM2:
            try:
                print(f"[Camera Init] Initializing Picamera2 at {self.width}x{self.height} (OV5647 sensor mode)...")
                self.picam2 = Picamera2()
                # 640x480 resolution mode (fastest mode for low-res CSI capture)
                config = self.picam2.create_video_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"}
                )
                self.picam2.configure(config)
                self.picam2.start()
                print("[Camera Init] Picamera2 started successfully!")
            except Exception as e:
                print(f"[Camera Init] Picamera2 failed: {e}. Trying OpenCV VideoCapture(0)...")
                self.picam2 = None

        if not self.picam2 and USE_CV2:
            try:
                print(f"[Camera Init] Initializing cv2 VideoCapture(0) at {self.width}x{self.height}...")
                self.cap = cv2.VideoCapture(0)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                if not self.cap.isOpened():
                    print("[Camera Init] cv2 VideoCapture(0) unavailable. Using synthetic frame generator.")
                    self.cap = None
                else:
                    print("[Camera Init] cv2 VideoCapture(0) ready!")
            except Exception as e:
                print(f"[Camera Init] cv2 init error: {e}")
                self.cap = None

    def get_frame_jpeg(self) -> bytes:
        if self.picam2:
            try:
                import io
                stream = io.BytesIO()
                self.picam2.capture_file(stream, format="jpeg")
                return stream.getvalue()
            except Exception as e:
                print(f"[Camera] Picam2 capture error: {e}")

        if self.cap:
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    _, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.quality])
                    return encoded.tobytes()
            except Exception as e:
                print(f"[Camera] cv2 capture error: {e}")

        # Fallback: Synthetic asphalt road frame for testing without physical camera
        return self._generate_synthetic_frame()

    def _generate_synthetic_frame(self) -> bytes:
        h, w = self.height, self.width
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (60, 60, 60)  # Asphalt gray background
        
        # Draw moving road lane markers
        t = time.time()
        offset = int((t * 120) % 60)
        for y in range(offset, h, 60):
            img[y:y+30, w//2-4:w//2+4] = (240, 240, 240)

        if USE_CV2:
            _, encoded = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), self.quality])
            return encoded.tobytes()
        else:
            try:
                from PIL import Image
                import io
                pil_img = Image.fromarray(img)
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=self.quality)
                return buf.getvalue()
            except Exception:
                return b""

    def release(self):
        print("[Camera Shutdown] Releasing camera hardware resources...")
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
                print("[Camera Shutdown] Picamera2 closed cleanly.")
            except Exception as e:
                print(f"[Camera Shutdown] Picam2 stop error: {e}")
        if self.cap:
            try:
                self.cap.release()
                print("[Camera Shutdown] cv2 VideoCapture released cleanly.")
            except Exception as e:
                print(f"[Camera Shutdown] cv2 release error: {e}")


class BufferQueue:
    """Basic offline queue: stores unsent frames on disk when connection fails."""
    def __init__(self, queue_dir: str = "./offline_queue"):
        self.queue_dir = queue_dir
        os.makedirs(self.queue_dir, exist_ok=True)

    def enqueue(self, frame_bytes: bytes, timestamp: float):
        filepath = os.path.join(self.queue_dir, f"frame_{int(timestamp*1000)}.jpg")
        try:
            with open(filepath, "wb") as f:
                f.write(frame_bytes)
        except Exception:
            pass

    def get_queued_files(self):
        files = glob.glob(os.path.join(self.queue_dir, "frame_*.jpg"))
        files.sort()
        return files

    def drain(self):
        for f in self.get_queued_files():
            try:
                os.remove(f)
            except Exception:
                pass


async def main():
    parser = argparse.ArgumentParser(description="PATCHSENSE Pi Zero 2 W Frame Streamer")
    parser.add_argument("--config", default="config.json", help="Path to config.json file")
    parser.add_argument("--server", help="Override server WebSocket URL (e.g. ws://192.168.1.105:8000/ws/ingest)")
    args = parser.parse_args()

    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), args.config)
    server_url = "ws://localhost:8000/ws/ingest"
    fps = 3
    jpeg_quality = 75
    width = 640
    height = 480
    queue_dir = "./offline_queue"

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = json.load(f)
            server_url = cfg.get("server_url", server_url)
            fps = cfg.get("fps", fps)
            jpeg_quality = cfg.get("jpeg_quality", jpeg_quality)
            width = cfg.get("width", width)
            height = cfg.get("height", height)
            queue_dir = cfg.get("queue_dir", queue_dir)

    if args.server:
        server_url = args.server

    print("=" * 65)
    print(" PATCHSENSE Raspberry Pi Zero 2 W Client Streamer")
    print(f" Target Server URL: {server_url}")
    print(f" Target Frame Rate: {fps} FPS | Resolution: {width}x{height}")
    print("=" * 65)

    camera = CameraCapture(width=width, height=height, jpeg_quality=jpeg_quality)
    buffer_queue = BufferQueue(queue_dir=queue_dir)
    frame_interval = 1.0 / max(1, fps)

    session_id = f"pi_{uuid.uuid4().hex[:6]}"

    try:
        while True:
            print(f"\n[Pi Streamer] Connecting to laptop server at {server_url}...")
            try:
                async with websockets.connect(server_url, ping_interval=10, ping_timeout=10) as ws:
                    print("[Pi Streamer] Connected successfully to laptop server!")
                    
                    # Drain offline queue if any frames buffered
                    queued_files = buffer_queue.get_queued_files()
                    if queued_files:
                        print(f"[BufferQueue] Transmitting {len(queued_files)} buffered offline frames...")
                        for qf in queued_files:
                            try:
                                with open(qf, "rb") as f:
                                    data = f.read()
                                await ws.send(data)
                                await asyncio.sleep(0.05)
                            except Exception:
                                break
                        buffer_queue.drain()

                    # Send session metadata header
                    meta_payload = json.dumps({
                        "type": "METADATA",
                        "session_id": session_id,
                        "device": "Pi Zero 2 W (OV5647)",
                        "timestamp": time.time()
                    })
                    await ws.send(meta_payload)

                    frames_sent = 0
                    t_session_start = time.time()

                    # Streaming Loop
                    while True:
                        t_start = time.time()
                        jpeg_bytes = camera.get_frame_jpeg()
                        
                        if jpeg_bytes:
                            # Send raw binary JPEG bytes over WebSocket
                            await ws.send(jpeg_bytes)
                            frames_sent += 1

                            # Print periodic summary every 10 frames to keep logs readable
                            if frames_sent % 10 == 0:
                                elapsed_total = time.time() - t_session_start
                                current_fps = frames_sent / max(1.0, elapsed_total)
                                print(f"[Pi Streamer] Sent {frames_sent} frames (avg {current_fps:.1f} FPS) -> Server OK")

                        # Rate throttling (~3 FPS)
                        elapsed = time.time() - t_start
                        sleep_time = max(0.0, frame_interval - elapsed)
                        await asyncio.sleep(sleep_time)

            except (websockets.exceptions.WebSocketException, OSError, ConnectionRefusedError) as e:
                print(f"[Pi Streamer] Connection lost: {e}. Retrying in 3 seconds...")
                # Buffer frame offline
                try:
                    frame_bytes = camera.get_frame_jpeg()
                    if frame_bytes:
                        buffer_queue.enqueue(frame_bytes, time.time())
                except Exception:
                    pass
                await asyncio.sleep(3)
            except Exception as e:
                print(f"[Pi Streamer] Unexpected error: {e}. Retrying in 3 seconds...")
                await asyncio.sleep(3)

    finally:
        camera.release()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Pi Streamer] KeyboardInterrupt received. Shutting down cleanly...")
