import os
import json
import uuid
import time
import random
import base64
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db, Base
from gps_tracker import gps_tracker
from detector import detector
from cluster import is_duplicate_detection

# Create tables
Base.metadata.create_all(bind=engine)

# Static directory for uploads
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="PATCHSENSE Pothole Detection Server", version="1.0.0")

# Enable CORS for local testing & multi-device dashboard connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for detection snapshots
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


class ConnectionManager:
    """Manages active live dashboard WebSocket connections."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS Manager] New dashboard connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS Manager] Dashboard disconnected. Remaining active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WS Manager] Broadcast error: {e}")
                to_remove.append(connection)
        for conn in to_remove:
            self.disconnect(conn)

manager = ConnectionManager()


@app.get("/")
def read_root():
    return {
        "system": "PATCHSENSE Pothole Detection & Road-Mapping System",
        "status": "online",
        "endpoints": {
            "ws_ingest": "/ws/ingest",
            "ws_gps": "/ws/gps",
            "ws_live": "/ws/live",
            "api_detections": "/api/detections",
            "api_stats": "/api/stats",
            "api_sim_trigger": "/api/sim/trigger"
        }
    }


# ==================== WEBSOCKET ENDPOINTS ==================== #

@app.websocket("/ws/ingest")
async def websocket_ingest(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    Endpoint for Pi Zero 2 W binary frame streaming.
    Receives binary JPEG bytes (or metadata JSON messages).
    """
    await websocket.accept()
    print("[Ingest WS] Pi camera connected!")
    session_id = str(uuid.uuid4())[:8]

    try:
        while True:
            # Receive either bytes or text
            message = await websocket.receive()
            frame_bytes = None
            client_ts = time.time()

            if "bytes" in message and message["bytes"]:
                frame_bytes = message["bytes"]
            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    if "timestamp" in data:
                        client_ts = data["timestamp"]
                    if "session_id" in data:
                        session_id = data["session_id"]
                    continue
                except Exception:
                    pass

            if not frame_bytes:
                continue

            # 1. Match timestamp to nearest GPS reading
            lat, lon, time_diff = gps_tracker.get_nearest_location(client_ts)

            # 2. Run object detection & draw bounding boxes on frame
            annotated_frame_bytes, detections = detector.process_frame(frame_bytes)

            # 3. Broadcast live camera feed frame to dashboard
            b64_frame = base64.b64encode(annotated_frame_bytes).decode('utf-8')
            await manager.broadcast({
                "type": "LIVE_FRAME",
                "image": f"data:image/jpeg;base64,{b64_frame}",
                "timestamp": client_ts,
                "has_detections": len(detections) > 0
            })

            if not detections:
                continue

            # 3. Process detections
            for det in detections:
                curr_dt = datetime.utcnow()
                
                # Check for spatial-temporal duplicate clustering (~15m, ~60s)
                if is_duplicate_detection(db, lat, lon, curr_dt, max_distance_meters=15.0, max_time_seconds=60.0):
                    print(f"[Cluster] Duplicate pothole ignored near ({lat:.5f}, {lon:.5f})")
                    continue

                # Save annotated snapshot image
                filename = f"pothole_{uuid.uuid4().hex[:10]}_{int(time.time())}.jpg"
                filepath = os.path.join(UPLOADS_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(det["annotated_image"])

                rel_image_path = f"/static/uploads/{filename}"

                # 4. Save to Database
                db_detection = models.Detection(
                    lat=lat,
                    lon=lon,
                    severity=det["severity"],
                    confidence=det["confidence"],
                    image_path=rel_image_path,
                    timestamp=curr_dt,
                    status="reported",
                    session_id=session_id,
                    bbox=json.dumps(det["bbox"])
                )
                db.add(db_detection)
                db.commit()
                db.refresh(db_detection)

                print(f"[DB] New Pothole #{db_detection.id} logged at ({lat:.5f}, {lon:.5f}) [{det['severity'].upper()}]")

                # 5. Broadcast to connected Live Dashboards
                payload = {
                    "type": "NEW_DETECTION",
                    "detection": {
                        "id": db_detection.id,
                        "lat": db_detection.lat,
                        "lon": db_detection.lon,
                        "severity": db_detection.severity,
                        "confidence": db_detection.confidence,
                        "image_path": db_detection.image_path,
                        "timestamp": db_detection.timestamp.isoformat(),
                        "status": db_detection.status,
                        "session_id": db_detection.session_id,
                        "bbox": db_detection.bbox
                    }
                }
                await manager.broadcast(payload)

    except WebSocketDisconnect:
        print("[Ingest WS] Pi camera disconnected.")
    except Exception as e:
        print(f"[Ingest WS] Error: {e}")


@app.websocket("/ws/gps")
async def websocket_gps(websocket: WebSocket):
    """
    Endpoint for Dashboard Browser continuous GPS streaming.
    Receives { "lat": float, "lon": float, "timestamp": float }.
    """
    await websocket.accept()
    print("[GPS WS] Dashboard GPS tracker connected!")
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
                lat = float(data["lat"])
                lon = float(data["lon"])
                ts = float(data.get("timestamp", time.time()))
                gps_tracker.update_location(lat, lon, ts)
            except Exception as e:
                print(f"[GPS WS] Parse error: {e}")
    except WebSocketDisconnect:
        print("[GPS WS] Dashboard GPS stream disconnected.")


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Endpoint for Dashboard to receive real-time detection broadcasts.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ==================== REST API ENDPOINTS ==================== #

@app.get("/api/detections", response_model=List[schemas.DetectionResponse])
def get_detections(
    status: Optional[str] = Query(None, description="Filter by status (reported, verified, fixed)"),
    severity: Optional[str] = Query(None, description="Filter by severity (high, medium, low)"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(models.Detection)
    if status:
        query = query.filter(models.Detection.status == status)
    if severity:
        query = query.filter(models.Detection.severity == severity)
    return query.order_by(models.Detection.timestamp.desc()).limit(limit).all()


@app.get("/api/detections/{detection_id}", response_model=schemas.DetectionResponse)
def get_detection(detection_id: int, db: Session = Depends(get_db)):
    det = db.query(models.Detection).filter(models.Detection.id == detection_id).first()
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")
    return det


@app.patch("/api/detections/{detection_id}/status", response_model=schemas.DetectionResponse)
async def update_detection_status(
    detection_id: int, 
    update_data: schemas.DetectionUpdateStatus, 
    db: Session = Depends(get_db)
):
    det = db.query(models.Detection).filter(models.Detection.id == detection_id).first()
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")

    if update_data.status not in ["reported", "verified", "fixed"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be 'reported', 'verified', or 'fixed'.")

    det.status = update_data.status
    db.commit()
    db.refresh(det)

    # Broadcast status change to live dashboard
    await manager.broadcast({
        "type": "STATUS_UPDATE",
        "detection_id": det.id,
        "status": det.status
    })

    return det


@app.get("/api/stats", response_model=schemas.StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(models.Detection).count()
    needs_verification = db.query(models.Detection).filter(models.Detection.status == "reported").count()
    verified = db.query(models.Detection).filter(models.Detection.status == "verified").count()
    fixed = db.query(models.Detection).filter(models.Detection.status == "fixed").count()
    
    high = db.query(models.Detection).filter(models.Detection.severity == "high").count()
    medium = db.query(models.Detection).filter(models.Detection.severity == "medium").count()
    low = db.query(models.Detection).filter(models.Detection.severity == "low").count()

    return {
        "total": total,
        "needs_verification": needs_verification,
        "verified": verified,
        "fixed": fixed,
        "high_severity": high,
        "medium_severity": medium,
        "low_severity": low
    }


@app.post("/api/gps")
def post_gps(gps: schemas.GPSPoint):
    """HTTP POST fallback for GPS pings."""
    gps_tracker.update_location(gps.lat, gps.lon, gps.timestamp)
    return {"status": "ok", "location": [gps.lat, gps.lon]}


@app.post("/api/sim/trigger")
async def trigger_simulated_detection(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    severity: Optional[str] = "high",
    db: Session = Depends(get_db)
):
    """
    Simulation / Demo helper endpoint.
    Creates a simulated pothole detection on demand with synthetic image & map location!
    """
    import cv2
    import numpy as np

    if lat is None or lon is None:
        curr_lat, curr_lon = gps_tracker.get_latest_location()
        # Add slight jitter to coordinates so markers don't overlap completely
        lat = curr_lat + random.uniform(-0.0008, 0.0008)
        lon = curr_lon + random.uniform(-0.0008, 0.0008)

    # Generate synthetic road image with pothole box
    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (70, 70, 70)  # Asphalt gray background
    
    # Draw road lines
    cv2.line(img, (w // 2, 0), (w // 2, h), (255, 255, 255), 4)
    
    # Draw synthetic pothole
    x1, y1 = random.randint(150, 250), random.randint(200, 300)
    x2, y2 = x1 + random.randint(120, 200), y1 + random.randint(80, 140)
    cv2.ellipse(img, ((x1+x2)//2, (y1+y2)//2), ((x2-x1)//2, (y2-y1)//2), 0, 0, 360, (30, 30, 30), -1)
    
    # Draw bounding box
    color = (0, 0, 255) if severity == "high" else ((0, 165, 255) if severity == "medium" else (0, 255, 0))
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
    conf = round(random.uniform(0.82, 0.97), 2)
    cv2.putText(img, f"Pothole {conf:.2f} ({severity.upper()})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    filename = f"sim_pothole_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(UPLOADS_DIR, filename)
    cv2.imwrite(filepath, img)

    # Broadcast synthetic frame to live camera feed panel
    _, img_encoded = cv2.imencode('.jpg', img)
    b64_sim = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
    await manager.broadcast({
        "type": "LIVE_FRAME",
        "image": f"data:image/jpeg;base64,{b64_sim}",
        "timestamp": time.time(),
        "has_detections": True
    })

    rel_image_path = f"/static/uploads/{filename}"
    curr_dt = datetime.utcnow()

    db_detection = models.Detection(
        lat=lat,
        lon=lon,
        severity=severity,
        confidence=conf,
        image_path=rel_image_path,
        timestamp=curr_dt,
        status="reported",
        session_id="simulated",
        bbox=json.dumps([x1, y1, x2, y2])
    )
    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)

    payload = {
        "type": "NEW_DETECTION",
        "detection": {
            "id": db_detection.id,
            "lat": db_detection.lat,
            "lon": db_detection.lon,
            "severity": db_detection.severity,
            "confidence": db_detection.confidence,
            "image_path": db_detection.image_path,
            "timestamp": db_detection.timestamp.isoformat(),
            "status": db_detection.status,
            "session_id": db_detection.session_id,
            "bbox": db_detection.bbox
        }
    }
    await manager.broadcast(payload)

    return {"status": "success", "detection": db_detection}


@app.post("/api/settings/stub-mode")
def set_stub_mode(enabled: bool = Query(..., description="Enable or disable stub detector mode")):
    detector.set_stub_mode(enabled)
    return {"stub_mode": detector.use_stub}
