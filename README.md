# PATCHSENSE — Real-time Pothole Detection & Road-Mapping System

**PATCHSENSE** is an end-to-end real-time pothole detection and spatial road-mapping system designed for vehicle-mounted deployment.

A **Raspberry Pi Zero 2 W** equipped with a camera captures video frames on the road and streams raw binary JPEG frames over WebSocket to an inference server running on a laptop. The server runs a **single-class YOLO object detector**, matches each frame to browser-based GPS readings, performs spatial-temporal clustering (~15m, ~60s deduplication), logs pothole hazards to a SQLite database, and broadcasts new detections live to a polished React + Leaflet dark-themed dashboard.

---

## 🏗 System Architecture

```
[ Raspberry Pi Zero 2 W ] 
      │ 
      ├── Raw Binary JPEG Frames (WebSocket: /ws/ingest)
      ▼
[ Laptop FastAPI Server ] ◄── Browser GPS Pings (navigator.geolocation.watchPosition)
      │
      ├── 1. Timestamp Matching (GPS Tracker)
      ├── 2. YOLO Object Detection (pothole class only)
      ├── 3. Spatial-Temporal Clustering (~15m, ~60s deduplication)
      ├── 4. SQLite DB Persistence & Image Snapshot Storage
      │
      └── Broadcast live detections (WebSocket: /ws/live) ──► [ React + Leaflet Dashboard ]
```

---
## Contibutions
1] Darshan.H : Build the entire software.

2] Amar.s : BUild the entire Architecture & entire hardware part integiration


## 🚀 Quick Start Guide

### 1. Server Setup (Laptop)

Navigate to the `server` directory and install Python dependencies:
```bash
cd server
pip install -r requirements.txt
```

Run the FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs: `http://localhost:8000/docs`
- Uploaded snapshots: `http://localhost:8000/static/uploads/`

> **Note on Stub Mode vs Trained YOLO Model**:
> The server starts with a built-in **Stub Detector** (~30% random simulated potholes) for instant pipeline testing.
> To deploy a custom-trained model, place your trained YOLO weights in `server/models/best.pt` or `server/models/yolo26n.pt`. The server automatically loads the custom model upon restart!

---

### 2. Dashboard Setup (Laptop Browser)

Navigate to the `dashboard` directory and install Node.js dependencies:
```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173` in your browser:
- Grant **Geolocation Permissions** when prompted.
- View live pothole markers appearing on the dark CartoDB map in real time.
- Click any marker to view the snapshot image, GPS tag, confidence score, and update its status (`reported`, `verified`, `fixed`).
- Click **"Simulate Detection"** in the header to trigger a synthetic detection instantly.

---

### 3. Raspberry Pi Client Setup (Raspberry Pi Zero 2 W)

Connect your Raspberry Pi and Laptop to the **same Wi-Fi hotspot**.

Navigate to `pi-client`:
```bash
cd pi-client
pip install -r requirements.txt
```

Edit `config.json` with your laptop's Wi-Fi IP address:
```json
{
  "server_url": "ws://192.168.1.105:8000/ws/ingest",
  "fps": 3,
  "jpeg_quality": 75
}
```

Run the camera streamer:
```bash
python main.py
```

---

## 🧠 Training Custom YOLO Model (Colab GPU)

To train a custom single-class YOLO model (`pothole`) using Roboflow datasets:

1. Open `training/README.md` or launch a Google Colab notebook with **GPU runtime**.
2. Download a pothole dataset from Roboflow (e.g., `BharatPothole` / `pothole-detection`).
3. Confirm `data.yaml` defines single class: `nc: 1`, `names: ['pothole']`.
4. Train for 50 epochs:
   ```python
   from ultralytics import YOLO
   model = YOLO("yolo26n.pt") # or yolov8n.pt
   model.train(data="path/to/data.yaml", epochs=50, imgsz=640, batch=16, patience=10)
   ```
5. Download `best.pt` and place it at `server/models/best.pt`.

---

## ⚠️ Known Limitations & Future Work

1. **Wi-Fi Browser Geolocation**: GPS coordinates are derived from the dashboard browser tab (`navigator.geolocation.watchPosition`). This relies on Wi-Fi positioning, which can have position lag or coarseness compared to dedicated hardware GPS modules (e.g. NEO-6M / GT-U7).
2. **Single-Class Model**: The system exclusively detects single-class potholes (`nc: 1`).
3. **Route Replay**: Historical route replay animations are omitted for demo scope; all detected hazards are mapped statically and dynamically as live points.
4. **Deep Offline Queue UI**: The Pi client includes local disk queueing (`./offline_queue`) when Wi-Fi drops, but a graphical UI for inspecting the queue is deferred to future work.
