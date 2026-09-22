import os
import sys

# Ensure server directory is always in sys.path so sibling imports work whether run from root or server/
server_dir = os.path.dirname(os.path.abspath(__file__))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

import json
import uuid
import time
import random
import base64
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

import cv2
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db, Base, SessionLocal, init_db
from gps_tracker import gps_tracker
from detector import detector, SAMPLE_LICENSE_PLATES
from cluster import is_duplicate_detection

# Initialize database tables and run schema migrations
init_db()

# Static directory for uploads
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(
    title="BEL UrbanSense — AI-Powered Mobile Urban Intelligence Platform",
    description="Bharat Electronics Limited Smart Automation Platform using Public Transport Bus Fleet",
    version="2.0.0"
)

# Enable CORS for local testing & multi-device dashboard connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def enforce_cloud_https(request: Request, call_next):
    # Enforce HTTPS on cloud deployment (Render/cloud proxy) so smartphone camera permissions work seamlessly
    proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    if proto == "http" and ("onrender.com" in host or "render.com" in host):
        query = f"?{request.url.query}" if request.url.query else ""
        return RedirectResponse(url=f"https://{host}{request.url.path}{query}", status_code=301)
    return await call_next(request)

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


# Seed default public transit bus fleet
def seed_default_fleet():
    db = SessionLocal()
    try:
        initial_fleet = [
            models.BusFleet(
                id="BUS-101",
                route_name="Route 42A - EM Bypass Arterial (Science City - Ruby)",
                current_lat=22.5726,
                current_lon=88.3639,
                speed_kmh=32.5,
                route_delay_min=1.5,
                passenger_load="Moderate",
                status="on_route",
                active_cameras="front,side,rear"
            ),
            models.BusFleet(
                id="BUS-104",
                route_name="Route 18B - VIP Road & Salt Lake Sector V",
                current_lat=22.5980,
                current_lon=88.3950,
                speed_kmh=21.0,
                route_delay_min=6.5,
                passenger_load="Crowded",
                status="delayed",
                active_cameras="front,side"
            )
        ]
        for b in initial_fleet:
            existing = db.query(models.BusFleet).filter(models.BusFleet.id == b.id).first()
            if not existing:
                db.add(b)
        db.commit()
    finally:
        db.close()

seed_default_fleet()


@app.get("/")
def read_root():
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {
        "platform": "BEL UrbanSense — AI Mobile Urban Intelligence Platform",
        "organization": "Bharat Electronics Limited",
        "status": "online"
    }

@app.get("/dashboard")
def get_dashboard_html():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "dashboard.html"))

@app.get("/camera")
def get_camera_html():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "camera.html"))

@app.get("/api/network_info")
def get_network_info(request: Request):
    host_header = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme

    # Automatically recognize Render or any public cloud deployment
    is_cloud = (
        "onrender.com" in host_header 
        or "render.com" in host_header 
        or (proto == "https" and not any(h in host_header for h in ["192.168.", "10.", "127.0.0.1", "localhost"]))
    )

    if is_cloud:
        base_url = f"https://{host_header}"
        return {
            "is_cloud": True,
            "lan_ip": None,
            "cloud_camera_url": f"{base_url}/camera",
            "https_camera_url": f"{base_url}/camera",
            "http_camera_url": f"{base_url}/camera",
            "dashboard_url": f"{base_url}/"
        }

    # Offline/Local LAN discovery for college Wi-Fi testing
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return {
        "is_cloud": False,
        "lan_ip": ip,
        "https_camera_url": f"https://{ip}:8443/camera",
        "http_camera_url": f"http://{ip}:8000/camera",
        "dashboard_url": f"http://{ip}:8000/"
    }

last_mobile_frame_time = 0.0

# Real-Time Independent Mobile Edge Unit State (Smartphone GPS & Connectivity)
mobile_gps_state = {
    "lat": 22.5726,
    "lon": 88.3639,
    "speed": 0.0,
    "accuracy": 10.0,
    "last_updated": 0.0,
    "connected": False
}

mobile_problem_focus = "auto"


# ==================== WEBSOCKET ENDPOINTS ==================== #

@app.websocket("/ws/ingest")
async def websocket_ingest(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    Endpoint for independent mobile phone camera streaming.
    Completely INDEPENDENT from fleet buses BUS-101 and BUS-104.
    """
    global last_mobile_frame_time, mobile_gps_state, mobile_problem_focus
    await websocket.accept()
    print("[Ingest WS] Independent Mobile Edge Sensing Unit connected!")
    session_id = str(uuid.uuid4())[:8]
    mobile_gps_state["connected"] = True

    # Notify dashboard that an independent mobile edge camera has connected
    await manager.broadcast({
        "type": "EDGE_CAMERA_STATUS",
        "connected": True,
        "bus_id": "MOBILE-CAM",
        "source": "mobile_camera",
        "problem_focus": mobile_problem_focus
    })

    camera_angle = "front"
    inbound_bus_id = "MOBILE-CAM"

    mobile_log_state = {
        "last_defect": 0.0,
        "last_congestion": 0.0,
        "last_anpr": 0.0,
        "last_pedestrian": 0.0,
        "last_infra": 0.0,
        "defects": 0,
        "congestion": 0,
        "anpr": 0,
        "pedestrian": 0,
        "infra": 0,
        "start_time": time.time()
    }

    latest_frame_data = None
    frame_ready = asyncio.Event()
    stop_event = asyncio.Event()

    async def rx_worker():
        nonlocal latest_frame_data, camera_angle, session_id
        global mobile_problem_focus, mobile_gps_state
        try:
            while not stop_event.is_set():
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                client_ts = time.time()

                if "bytes" in message and message["bytes"]:
                    # Latest frame buffer: always drops stale intermediate frames (Zero lag accumulation!)
                    latest_frame_data = (message["bytes"], client_ts)
                    frame_ready.set()
                elif "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                        if "timestamp" in data:
                            client_ts = float(data["timestamp"])
                        if "session_id" in data:
                            session_id = data["session_id"]
                        if "camera_angle" in data:
                            camera_angle = data["camera_angle"]
                        if "problem_focus" in data:
                            mobile_problem_focus = data["problem_focus"]
                            await manager.broadcast({
                                "type": "MOBILE_FOCUS_UPDATE",
                                "focus": mobile_problem_focus
                            })
                        elif "problem_mode" in data:
                            mobile_problem_focus = data["problem_mode"]
                            await manager.broadcast({
                                "type": "MOBILE_FOCUS_UPDATE",
                                "focus": mobile_problem_focus
                            })
                        # Update exact GPS if sent in message
                        if "lat" in data and "lon" in data:
                            mobile_gps_state["lat"] = float(data["lat"])
                            mobile_gps_state["lon"] = float(data["lon"])
                            mobile_gps_state["speed"] = float(data.get("speed", 0.0))
                            mobile_gps_state["accuracy"] = float(data.get("accuracy", 10.0))
                            mobile_gps_state["last_updated"] = time.time()
                            await manager.broadcast({
                                "type": "MOBILE_LOCATION_UPDATE",
                                "lat": mobile_gps_state["lat"],
                                "lon": mobile_gps_state["lon"],
                                "speed": mobile_gps_state["speed"],
                                "accuracy": mobile_gps_state["accuracy"],
                                "bus_id": "MOBILE-CAM",
                                "timestamp": client_ts
                            })
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            stop_event.set()
            frame_ready.set()

    async def tx_worker():
        nonlocal latest_frame_data
        global last_mobile_frame_time
        try:
            while not stop_event.is_set():
                await frame_ready.wait()
                frame_ready.clear()
                if stop_event.is_set():
                    break
                if latest_frame_data is None:
                    continue

                frame_bytes, client_ts = latest_frame_data
                latest_frame_data = None

                # Update active mobile streaming timestamp
                last_mobile_frame_time = time.time()

                # 1. Use the EXACT real-time GPS coordinates of the mobile phone
                lat = mobile_gps_state["lat"]
                lon = mobile_gps_state["lon"]
                speed = mobile_gps_state["speed"]

                # 2. Run multi-task urban inference asynchronously in thread pool (ZERO event-loop blocking)
                annotated_frame_bytes, detections = await asyncio.to_thread(
                    detector.process_frame,
                    frame_bytes, 
                    camera_angle=camera_angle,
                    bus_id="MOBILE-CAM",
                    problem_focus=mobile_problem_focus
                )

                # Send lightweight JSON perception status directly to the mobile phone (<100 bytes, zero lag)
                try:
                    await websocket.send_json({
                        "type": "MOBILE_PERCEPTION_STATUS",
                        "has_detections": len(detections) > 0,
                        "event_type": detections[0].get("event_type") if detections else None,
                        "subtype": detections[0].get("subtype") if detections else None,
                        "severity": detections[0].get("severity", "medium") if detections else "normal",
                        "vehicle_count": detections[0].get("vehicle_count", 0) if detections else 0,
                        "plate_number": detections[0].get("plate_number") if detections else None,
                        "is_indoor": getattr(detector, "cached_is_indoor", False),
                        "timestamp": client_ts
                    })
                except Exception:
                    pass

                # 3. Broadcast live camera feed with telemetry to dashboard clients
                b64_frame = base64.b64encode(annotated_frame_bytes).decode('utf-8')
                await manager.broadcast({
                    "type": "LIVE_FRAME",
                    "image": f"data:image/jpeg;base64,{b64_frame}",
                    "timestamp": client_ts,
                    "has_detections": len(detections) > 0,
                    "detection_subtype": detections[0].get("subtype", detections[0].get("event_type", "pothole")) if detections else None,
                    "event_type": detections[0].get("event_type", "road_defect") if detections else None,
                    "camera_angle": camera_angle,
                    "bus_id": "MOBILE-CAM",
                    "gps": {"lat": lat, "lon": lon},
                    "speed": speed,
                    "source": "mobile_camera",
                    "is_mobile": True,
                    "problem_focus": mobile_problem_focus
                })

                if not detections:
                    continue

                # 4. Save detections to Database with Realistic Pacing (avoids DB lock & frame drops)
                now_time = time.time()
                time_since_def = now_time - mobile_log_state["last_defect"] if mobile_log_state["last_defect"] > 0 else (now_time - mobile_log_state["start_time"])
                time_since_cong = now_time - mobile_log_state["last_congestion"] if mobile_log_state["last_congestion"] > 0 else (now_time - mobile_log_state["start_time"])
                time_since_anpr = now_time - mobile_log_state["last_anpr"] if mobile_log_state["last_anpr"] > 0 else (now_time - mobile_log_state["start_time"])
                time_since_ped = now_time - mobile_log_state["last_pedestrian"] if mobile_log_state["last_pedestrian"] > 0 else (now_time - mobile_log_state["start_time"])
                time_since_infra = now_time - mobile_log_state["last_infra"] if mobile_log_state["last_infra"] > 0 else (now_time - mobile_log_state["start_time"])

                events_to_log = []
                for det in detections:
                    det_type = det.get("event_type", "road_defect")
                    det_sub = det.get("subtype", "pothole")
                    is_anpr = bool(det.get("plate_number"))
                    is_traffic = (det_type == "traffic_bottleneck")
                    is_ped = (det_type == "pedestrian_safety")
                    is_infra = (det_type == "missing_infrastructure" or "divider" in det_sub or "signboard" in det_sub or "crossing" in det_sub)

                    if is_anpr and (time_since_anpr >= 18.0):
                        mobile_log_state["last_anpr"] = now_time
                        mobile_log_state["anpr"] += 1
                        events_to_log.append(det)
                    elif is_traffic and ((mobile_log_state["last_congestion"] == 0.0 and time_since_cong >= 3.0) or (time_since_cong >= 12.0)):
                        mobile_log_state["last_congestion"] = now_time
                        mobile_log_state["congestion"] += 1
                        events_to_log.append(det)
                    elif is_ped and ((mobile_log_state["last_pedestrian"] == 0.0 and time_since_ped >= 3.0) or (time_since_ped >= 14.0)):
                        mobile_log_state["last_pedestrian"] = now_time
                        mobile_log_state["pedestrian"] += 1
                        events_to_log.append(det)
                    elif is_infra and ((mobile_log_state["last_infra"] == 0.0 and time_since_infra >= 3.0) or (time_since_infra >= 15.0)):
                        mobile_log_state["last_infra"] = now_time
                        mobile_log_state["infra"] += 1
                        events_to_log.append(det)
                    elif not is_anpr and not is_traffic and not is_ped and not is_infra and ((mobile_log_state["last_defect"] == 0.0 and time_since_def >= 2.5) or (time_since_def >= 7.0)):
                        mobile_log_state["last_defect"] = now_time
                        mobile_log_state["defects"] += 1
                        events_to_log.append(det)

                if not events_to_log:
                    continue

                curr_dt = datetime.utcnow()
                for det in events_to_log:
                    try:
                        det_type = det.get("event_type", "road_defect")
                        det_sub = det.get("subtype", "pothole")
                        det_plate = det.get("plate_number")
                        if is_duplicate_detection(db, lat, lon, curr_dt, max_distance_meters=8.0, max_time_seconds=25.0, event_type=det_type, plate_number=det_plate):
                            continue

                        filename = f"mobile_{uuid.uuid4().hex[:10]}_{int(time.time())}.jpg"
                        filepath = os.path.join(UPLOADS_DIR, filename)
                        snap_data = det.get("annotated_image") or annotated_frame_bytes
                        with open(filepath, "wb") as f:
                            f.write(snap_data)

                        rel_image_path = f"/static/uploads/{filename}"

                        is_traffic = (det_type == "traffic_bottleneck")
                        is_anpr = bool(det.get("plate_number"))
                        is_ped = (det_type == "pedestrian_safety")
                        is_infra = (det_type == "missing_infrastructure" or "divider" in det_sub or "signboard" in det_sub)

                        if is_anpr:
                            road_desc = f"Mobile ANPR: {det.get('plate_number')} [{det_sub.upper()}] ({lat:.5f}° N, {lon:.5f}° E)"
                        elif is_traffic:
                            road_desc = f"Live Mobile Traffic Congestion Corridor ({lat:.5f}° N, {lon:.5f}° E)"
                        elif is_ped:
                            road_desc = f"Live Mobile Pedestrian Safety Zone: {det_sub.replace('_', ' ').title()} ({lat:.5f}° N, {lon:.5f}° E)"
                        elif is_infra:
                            road_desc = f"Live Mobile Infrastructure Defect: {det_sub.replace('_', ' ').title()} ({lat:.5f}° N, {lon:.5f}° E)"
                        elif det_sub == "waterlogging":
                            road_desc = f"Live Mobile Waterlogged Road Surface ({lat:.5f}° N, {lon:.5f}° E)"
                        else:
                            road_desc = f"Live Mobile Road Pothole Hazard ({lat:.5f}° N, {lon:.5f}° E)"

                        db_detection = models.Detection(
                            lat=lat,
                            lon=lon,
                            severity=det.get("severity", "high" if (is_traffic or is_anpr) else "medium"),
                            confidence=det.get("confidence", 0.90),
                            image_path=rel_image_path,
                            timestamp=curr_dt,
                            status="reported",
                            event_type=det_type,
                            subtype=det_sub,
                            bus_id="MOBILE-CAM",
                            route_id="Mobile-Survey",
                            camera_angle=camera_angle,
                            road_name=road_desc,
                            vehicle_density=det.get("vehicle_density", 0.0),
                            vehicle_count=det.get("vehicle_count", 0),
                            plate_number=det.get("plate_number"),
                            plate_confidence=det.get("plate_confidence", 0.0),
                            session_id=session_id,
                            bbox=json.dumps(det.get("bbox", [0, 0, 0, 0]))
                        )
                        db.add(db_detection)
                        db.commit()
                        db.refresh(db_detection)

                        if db_detection.plate_number:
                            print(f"[BACKEND-MOBILE] [!] ANPR DETECTED: Plate={db_detection.plate_number} | Offense={db_detection.subtype} | Match={int(db_detection.plate_confidence*100)}% | GPS=({lat:.5f}, {lon:.5f})", flush=True)
                        elif is_traffic:
                            print(f"[BACKEND-MOBILE] [*] TRAFFIC CONGESTION: Vehicles={db_detection.vehicle_count} | Density={int(db_detection.vehicle_density*100)}% | GPS=({lat:.5f}, {lon:.5f})", flush=True)
                        elif is_ped:
                            print(f"[BACKEND-MOBILE] [🚸] PEDESTRIAN SAFETY: {db_detection.subtype} | GPS=({lat:.5f}, {lon:.5f})", flush=True)
                        elif is_infra:
                            print(f"[BACKEND-MOBILE] [🚧] INFRA DEFECT: {db_detection.subtype} | GPS=({lat:.5f}, {lon:.5f})", flush=True)
                        else:
                            print(f"[BACKEND-MOBILE] [+] ROAD HAZARD: {db_detection.subtype.upper()} ({db_detection.severity}) | GPS=({lat:.5f}, {lon:.5f})", flush=True)

                        # Broadcast new event to dashboard with is_mobile=True and exact GPS
                        await manager.broadcast({
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
                                "event_type": db_detection.event_type,
                                "subtype": db_detection.subtype,
                                "bus_id": "MOBILE-CAM",
                                "road_name": db_detection.road_name,
                                "plate_number": db_detection.plate_number,
                                "plate_confidence": db_detection.plate_confidence,
                                "is_mobile": True
                            }
                        })
                    except Exception as log_err:
                        print(f"[Ingest WS] Incident log warning: {log_err}")
                        try:
                            db.rollback()
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Ingest WS] Worker exception: {e}")
        finally:
            stop_event.set()

    try:
        rx_task = asyncio.create_task(rx_worker())
        tx_task = asyncio.create_task(tx_worker())
        done, pending = await asyncio.wait(
            [rx_task, tx_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        stop_event.set()
        frame_ready.set()
        for t in pending:
            t.cancel()
    except WebSocketDisconnect:
        print("[Ingest WS] Independent mobile camera disconnected.")
    except Exception as e:
        print(f"[Ingest WS] Error: {e}")
    finally:
        mobile_gps_state["connected"] = False
        await manager.broadcast({
            "type": "EDGE_CAMERA_STATUS",
            "connected": False,
            "bus_id": "MOBILE-CAM",
            "source": "mobile_camera"
        })


@app.websocket("/ws/gps")
async def websocket_gps(websocket: WebSocket):
    global mobile_gps_state
    await websocket.accept()
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
                lat = float(data["lat"])
                lon = float(data["lon"])
                speed = float(data.get("speed", 0.0))
                acc = float(data.get("accuracy", 10.0))
                ts = float(data.get("timestamp", time.time()))
                bus_id = data.get("bus_id", "MOBILE-CAM")

                if bus_id == "MOBILE-CAM" or data.get("source") == "mobile_camera":
                    mobile_gps_state["lat"] = lat
                    mobile_gps_state["lon"] = lon
                    mobile_gps_state["speed"] = speed
                    mobile_gps_state["accuracy"] = acc
                    mobile_gps_state["last_updated"] = time.time()
                    mobile_gps_state["connected"] = True

                    # Broadcast exact mobile unit location to dashboard map!
                    await manager.broadcast({
                        "type": "MOBILE_LOCATION_UPDATE",
                        "lat": lat,
                        "lon": lon,
                        "speed": speed,
                        "accuracy": acc,
                        "bus_id": "MOBILE-CAM",
                        "timestamp": ts
                    })
                else:
                    gps_tracker.update_location(lat, lon, ts)
                    db_s = SessionLocal()
                    try:
                        b_record = db_s.query(models.BusFleet).filter(models.BusFleet.id == bus_id).first()
                        if b_record:
                            b_record.current_lat = lat
                            b_record.current_lon = lon
                            db_s.commit()
                    finally:
                        db_s.close()
            except Exception:
                pass
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ==================== REST API ENDPOINTS ==================== #

@app.post("/api/mobile/focus")
async def set_mobile_focus(mode: str = Query("auto")):
    global mobile_problem_focus
    mobile_problem_focus = mode
    await manager.broadcast({
        "type": "MOBILE_FOCUS_UPDATE",
        "focus": mobile_problem_focus
    })
    return {"status": "success", "focus": mobile_problem_focus}

@app.get("/api/mobile/focus")
def get_mobile_focus():
    global mobile_problem_focus
    return {"focus": mobile_problem_focus}

@app.get("/api/detections", response_model=List[schemas.DetectionResponse])
def get_detections(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    bus_id: Optional[str] = Query(None),
    limit: int = Query(250, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(models.Detection)
    if bus_id and bus_id != "ALL":
        query = query.filter(models.Detection.bus_id == bus_id)
    if status:
        query = query.filter(models.Detection.status == status)
    if severity:
        query = query.filter(models.Detection.severity == severity)
    if event_type:
        query = query.filter(models.Detection.event_type == event_type)
    return query.order_by(models.Detection.timestamp.desc()).limit(limit).all()


@app.get("/api/fleet", response_model=List[schemas.BusFleetResponse])
def get_fleet(db: Session = Depends(get_db)):
    """Returns real-time status of the public transport bus fleet including active and diversion routes."""
    fleet = db.query(models.BusFleet).all()
    results = []
    for b in fleet:
        cfg = BUS_ROUTES_CONFIG.get(b.id, {})
        results.append(schemas.BusFleetResponse(
            id=b.id,
            route_name=b.route_name,
            current_lat=b.current_lat,
            current_lon=b.current_lon,
            speed_kmh=b.speed_kmh,
            route_delay_min=b.route_delay_min,
            passenger_load=b.passenger_load,
            status="rerouted" if cfg.get("is_rerouted") else "on_route",
            active_cameras=b.active_cameras,
            last_update=b.last_update or datetime.utcnow(),
            is_rerouted=cfg.get("is_rerouted", False),
            hazard_reason=cfg.get("hazard_reason", ""),
            scheduled_waypoints=cfg.get("scheduled_waypoints", []),
            hazard_segment=cfg.get("hazard_segment", []),
            reroute_waypoints=cfg.get("reroute_waypoints", []),
            detour_segment=cfg.get("detour_segment", [])
        ))
    return results


@app.get("/api/fleet/{bus_id}", response_model=schemas.BusFleetResponse)
def get_bus_by_id(bus_id: str, db: Session = Depends(get_db)):
    """Checks if a specific bus exists in the database and returns its live telemetry and route status."""
    bus = db.query(models.BusFleet).filter(models.BusFleet.id == bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail=f"Bus '{bus_id}' not found in database")
    cfg = BUS_ROUTES_CONFIG.get(bus.id, {})
    return schemas.BusFleetResponse(
        id=bus.id,
        route_name=bus.route_name,
        current_lat=bus.current_lat,
        current_lon=bus.current_lon,
        speed_kmh=bus.speed_kmh,
        route_delay_min=bus.route_delay_min,
        passenger_load=bus.passenger_load,
        status="rerouted" if cfg.get("is_rerouted") else (bus.status or "on_route"),
        active_cameras=bus.active_cameras or "front",
        last_update=bus.last_update or datetime.utcnow(),
        is_rerouted=cfg.get("is_rerouted", False),
        hazard_reason=cfg.get("hazard_reason", ""),
        scheduled_waypoints=cfg.get("scheduled_waypoints", []),
        hazard_segment=cfg.get("hazard_segment", []),
        reroute_waypoints=cfg.get("reroute_waypoints", []),
        detour_segment=cfg.get("detour_segment", [])
    )


@app.post("/api/fleet", response_model=schemas.BusFleetResponse, status_code=201)
async def register_bus(bus_data: schemas.BusCreate, db: Session = Depends(get_db)):
    """
    Registers a new public transit bus in the database and adds it to the live fleet tracking system.
    Immediately broadcasts the new bus to the live dashboard via WebSockets.
    """
    bid = bus_data.id.strip().upper()
    existing = db.query(models.BusFleet).filter(models.BusFleet.id == bid).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Bus ID '{bid}' is already registered in database")
    
    new_bus = models.BusFleet(
        id=bid,
        route_name=bus_data.route_name.strip(),
        current_lat=float(bus_data.current_lat),
        current_lon=float(bus_data.current_lon),
        speed_kmh=float(bus_data.speed_kmh) if bus_data.speed_kmh is not None else 25.0,
        route_delay_min=float(bus_data.route_delay_min) if bus_data.route_delay_min is not None else 0.0,
        passenger_load=bus_data.passenger_load or "Moderate",
        status=bus_data.status or "on_route",
        active_cameras=bus_data.active_cameras or "front",
        last_update=datetime.utcnow()
    )
    db.add(new_bus)
    db.commit()
    db.refresh(new_bus)

    # Register in route configuration so tracking, rerouting, and simulation work
    waypoints = bus_data.waypoints if bus_data.waypoints and len(bus_data.waypoints) > 0 else [[new_bus.current_lat, new_bus.current_lon]]
    BUS_ROUTES_CONFIG[new_bus.id] = {
        "route_name": new_bus.route_name,
        "is_rerouted": False,
        "scheduled_waypoints": waypoints,
        "hazard_segment": [],
        "reroute_waypoints": waypoints,
        "detour_segment": [],
        "hazard_reason": ""
    }

    # Broadcast to live dashboard via WebSocket
    await manager.broadcast({
        "type": "BUS_ADDED",
        "bus_id": new_bus.id,
        "route_name": new_bus.route_name,
        "lat": new_bus.current_lat,
        "lon": new_bus.current_lon,
        "speed_kmh": new_bus.speed_kmh,
        "status": new_bus.status
    })

    return schemas.BusFleetResponse(
        id=new_bus.id,
        route_name=new_bus.route_name,
        current_lat=new_bus.current_lat,
        current_lon=new_bus.current_lon,
        speed_kmh=new_bus.speed_kmh,
        route_delay_min=new_bus.route_delay_min,
        passenger_load=new_bus.passenger_load,
        status=new_bus.status,
        active_cameras=new_bus.active_cameras,
        last_update=new_bus.last_update,
        is_rerouted=False,
        hazard_reason="",
        scheduled_waypoints=waypoints,
        hazard_segment=[],
        reroute_waypoints=waypoints,
        detour_segment=[]
    )


@app.delete("/api/fleet/{bus_id}")
async def delete_bus(bus_id: str, db: Session = Depends(get_db)):
    """
    Deletes / decommissions a bus from the database and fleet tracking system.
    Immediately updates the live GIS dashboard via WebSockets.
    """
    bid = bus_id.strip().upper()
    bus = db.query(models.BusFleet).filter(models.BusFleet.id == bid).first()
    if not bus:
        raise HTTPException(status_code=404, detail=f"Bus '{bid}' not found in database")
    
    db.delete(bus)
    db.commit()

    if bid in BUS_ROUTES_CONFIG and bid not in ["BUS-101", "BUS-104"]:
        del BUS_ROUTES_CONFIG[bid]

    await manager.broadcast({
        "type": "BUS_REMOVED",
        "bus_id": bid
    })

    return {
        "status": "success",
        "message": f"Bus '{bid}' has been successfully removed from database and fleet system."
    }


b104_manual_override_expiry = 0.0

@app.post("/api/fleet/{bus_id}/reroute")
async def toggle_bus_reroute(
    bus_id: str,
    enable: Optional[bool] = None,
    reason: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Dynamically activates or resets route diversion/detour around road defects for any bus."""
    global b104_manual_override_expiry
    if bus_id not in BUS_ROUTES_CONFIG:
        raise HTTPException(status_code=404, detail="Bus ID not found")
    
    cfg = BUS_ROUTES_CONFIG[bus_id]

    if request:
        try:
            body = await request.json()
            if isinstance(body, dict):
                if "reroute" in body:
                    enable = body["reroute"]
                elif "enable" in body:
                    enable = body["enable"]
                if "reason" in body:
                    reason = body["reason"]
        except Exception:
            pass

    if enable is not None:
        cfg["is_rerouted"] = enable
    else:
        cfg["is_rerouted"] = not cfg["is_rerouted"]
    
    if bus_id == "BUS-104":
        # Keep user's manual toggle for 45s before resuming autonomous simulation
        b104_manual_override_expiry = time.time() + 45.0
    
    if reason:
        cfg["hazard_reason"] = reason

    bus = db.query(models.BusFleet).filter(models.BusFleet.id == bus_id).first()
    if bus:
        bus.status = "rerouted" if cfg["is_rerouted"] else "on_route"
        db.commit()

    event_payload = {
        "type": "ROUTE_REROUTE_EVENT",
        "bus_id": bus_id,
        "rerouted": cfg["is_rerouted"],
        "is_rerouted": cfg["is_rerouted"],
        "reason": cfg["hazard_reason"],
        "route_name": cfg["route_name"],
        "hazard_segment": cfg["hazard_segment"],
        "detour_route": cfg["reroute_waypoints"],
        "detour_segment": cfg.get("detour_segment"),
        "scheduled_route": cfg["scheduled_waypoints"]
    }
    await manager.broadcast(event_payload)
    return {
        "status": "success",
        "bus_id": bus_id,
        "is_rerouted": cfg["is_rerouted"],
        "rerouted": cfg["is_rerouted"],
        "reason": cfg["hazard_reason"]
    }


@app.get("/api/incidents/offending")
def get_offending_incidents(bus_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Returns detected rash driving and hit-and-run incidents with ANPR license plates."""
    query = db.query(models.Detection).filter(
        models.Detection.event_type == "offending_vehicle"
    )
    if bus_id and bus_id != "ALL":
        query = query.filter(models.Detection.bus_id == bus_id)
    incidents = query.order_by(models.Detection.timestamp.desc()).limit(20).all()
    return incidents


@app.get("/api/analytics/congestion")
def get_congestion_analytics(db: Session = Depends(get_db)):
    """Returns traffic density, bottlenecks, and route delay analytics."""
    fleet = db.query(models.BusFleet).all()
    avg_speed = sum(b.speed_kmh for b in fleet) / len(fleet) if fleet else 30.0
    avg_delay = sum(b.route_delay_min for b in fleet) / len(fleet) if fleet else 2.0

    return {
        "status": "optimal" if avg_speed > 25 else "congested",
        "avg_fleet_speed_kmh": round(avg_speed, 1),
        "avg_route_delay_min": round(avg_delay, 1),
        "bottlenecks": [
            {"corridor": "EM Bypass Arterial (Route 42A)", "congestion_level": "MODERATE", "delay_min": 1.5},
            {"corridor": "VIP Road & Salt Lake Sector V (Route 18B)", "congestion_level": "HEAVY BOTTLENECK", "delay_min": 6.5}
        ]
    }


@app.get("/api/analytics/infrastructure")
def get_infrastructure_analytics(bus_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Returns infrastructure deficiency counts for PWD maintenance planning."""
    query = db.query(models.Detection)
    if bus_id and bus_id != "ALL":
        query = query.filter(models.Detection.bus_id == bus_id)

    potholes = query.filter(models.Detection.subtype == "pothole").count()
    waterlogging = query.filter(models.Detection.subtype == "waterlogging").count()
    missing_dividers = query.filter(models.Detection.subtype == "missing_road_divider").count()
    missing_zebra = query.filter(models.Detection.subtype == "missing_zebra_crossing").count()
    damaged_signs = query.filter(models.Detection.subtype == "damaged_signboard").count()

    return {
        "total_defects": potholes + waterlogging + missing_dividers + missing_zebra + damaged_signs,
        "potholes": potholes,
        "waterlogging": waterlogging,
        "missing_road_dividers": missing_dividers,
        "missing_zebra_crossings": missing_zebra,
        "damaged_signboards": damaged_signs
    }


@app.patch("/api/detections/{detection_id}/status", response_model=schemas.DetectionResponse)
async def update_detection_status(
    detection_id: int, 
    update_data: schemas.DetectionUpdateStatus, 
    db: Session = Depends(get_db)
):
    det = db.query(models.Detection).filter(models.Detection.id == detection_id).first()
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")

    det.status = update_data.status
    db.commit()
    db.refresh(det)

    await manager.broadcast({
        "type": "STATUS_UPDATE",
        "detection_id": det.id,
        "status": det.status
    })
    return det


@app.get("/api/stats", response_model=schemas.StatsResponse)
def get_stats(bus_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Detection)
    if bus_id and bus_id != "ALL":
        query = query.filter(models.Detection.bus_id == bus_id)

    total = query.count()
    needs_verification = query.filter(models.Detection.status == "reported").count()
    verified = query.filter(models.Detection.status == "verified").count()
    fixed = query.filter(models.Detection.status == "fixed").count()
    
    high = query.filter(models.Detection.severity == "high").count()
    medium = query.filter(models.Detection.severity == "medium").count()
    low = query.filter(models.Detection.severity == "low").count()

    total_road_defects = query.filter(models.Detection.event_type == "road_defect").count()
    total_congestion = query.filter(models.Detection.event_type == "traffic_bottleneck").count()
    total_pedestrian = query.filter(models.Detection.event_type == "pedestrian_safety").count()
    total_offending = query.filter(models.Detection.event_type == "offending_vehicle").count()

    fleet_query = db.query(models.BusFleet)
    if bus_id and bus_id != "ALL":
        fleet = fleet_query.filter(models.BusFleet.id == bus_id).all()
        if fleet:
            avg_delay = fleet[0].route_delay_min
            active_buses = 1
        elif bus_id == "MOBILE-CAM":
            avg_delay = 0.0
            active_buses = 1
        else:
            avg_delay = 0.0
            active_buses = 0
    else:
        fleet = fleet_query.all()
        avg_delay = sum(b.route_delay_min for b in fleet) / len(fleet) if fleet else 2.0
        active_buses = len(fleet)

    return {
        "total": total,
        "needs_verification": needs_verification,
        "verified": verified,
        "fixed": fixed,
        "high_severity": high,
        "medium_severity": medium,
        "low_severity": low,
        "total_road_defects": total_road_defects,
        "total_congestion_zones": total_congestion,
        "total_pedestrian_risks": total_pedestrian,
        "total_offending_vehicles": total_offending,
        "active_buses": active_buses,
        "avg_fleet_delay_min": round(avg_delay, 1)
    }


@app.post("/api/sim/trigger")
async def trigger_simulated_detection(
    event_type: str = Query("road_defect", description="road_defect, offending_vehicle, traffic_bottleneck, pedestrian_safety, missing_infrastructure"),
    subtype: Optional[str] = None,
    severity: Optional[str] = "high",
    bus_id: str = "BUS-101",
    db: Session = Depends(get_db)
):
    """
    Simulation Trigger for Hackathon Presentations.
    Generates any BEL urban event (Offending ANPR vehicle, Traffic Bottleneck, School Crossing, Infrastructure defect)
    with realistic coordinates, images, and live broadcast.
    """
    curr_lat, curr_lon = gps_tracker.get_latest_location()
    lat = curr_lat + random.uniform(-0.0012, 0.0012)
    lon = curr_lon + random.uniform(-0.0012, 0.0012)

    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (60, 60, 60)
    cv2.line(img, (w // 2, 0), (w // 2, h), (255, 255, 255), 4)

    plate_num = None
    plate_conf = 0.0
    actual_subtype = subtype or "pothole"

    if event_type == "offending_vehicle":
        actual_subtype = "rash_driving"
        plate_num = random.choice(SAMPLE_LICENSE_PLATES)
        plate_conf = round(random.uniform(0.92, 0.98), 2)
        cv2.rectangle(img, (180, 150), (460, 380), (0, 0, 255), 3)
        cv2.putText(img, f"ANPR: {plate_num} [RASH DRIVING]", (180, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
    elif event_type == "traffic_bottleneck":
        actual_subtype = "heavy_congestion"
        cv2.rectangle(img, (100, 140), (540, 420), (0, 215, 255), 3)
        cv2.putText(img, "TRAFFIC BOTTLENECK - 24 VEHICLES", (100, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 215, 255), 2)
    elif event_type == "pedestrian_safety":
        actual_subtype = "school_children_crossing"
        cv2.rectangle(img, (400, 200), (520, 420), (255, 0, 180), 3)
        cv2.putText(img, "ALERT: SCHOOL ZONE PEDESTRIAN", (350, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 180), 2)
    elif event_type == "missing_infrastructure":
        event_type = "road_defect"
        actual_subtype = random.choice(["missing_road_divider", "missing_zebra_crossing", "damaged_signboard"])
        cv2.rectangle(img, (50, 220), (350, 420), (0, 165, 255), 3)
        cv2.putText(img, f"INFRA: {actual_subtype.upper()}", (50, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    else:
        actual_subtype = "pothole"
        cv2.ellipse(img, (320, 280), (90, 50), 0, 0, 360, (20, 20, 20), -1)
        cv2.rectangle(img, (220, 220), (420, 340), (0, 0, 255), 3)
        cv2.putText(img, "POTHOLE 0.96 [HIGH]", (220, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

    filename = f"sim_bel_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(UPLOADS_DIR, filename)
    cv2.imwrite(filepath, img)

    # Broadcast live camera preview
    _, img_encoded = cv2.imencode('.jpg', img)
    b64_sim = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
    await manager.broadcast({
        "type": "LIVE_FRAME",
        "image": f"data:image/jpeg;base64,{b64_sim}",
        "timestamp": time.time(),
        "has_detections": True,
        "bus_id": bus_id,
        "gps": {"lat": lat, "lon": lon}
    })

    curr_dt = datetime.utcnow()
    db_det = models.Detection(
        lat=lat,
        lon=lon,
        severity=severity,
        confidence=0.95,
        image_path=f"/static/uploads/{filename}",
        timestamp=curr_dt,
        status="reported",
        event_type=event_type,
        subtype=actual_subtype,
        bus_id=bus_id,
        route_id="Route-42A",
        camera_angle="front",
        road_name="EM Bypass Arterial Corridor, Kolkata",
        vehicle_density=0.85 if event_type == "traffic_bottleneck" else 0.0,
        vehicle_count=24 if event_type == "traffic_bottleneck" else 0,
        plate_number=plate_num,
        plate_confidence=plate_conf,
        session_id="simulated",
        bbox=json.dumps([180, 150, 460, 380])
    )
    db.add(db_det)
    db.commit()
    db.refresh(db_det)

    payload = {
        "type": "NEW_DETECTION",
        "detection": {
            "id": db_det.id,
            "lat": db_det.lat,
            "lon": db_det.lon,
            "severity": db_det.severity,
            "confidence": db_det.confidence,
            "image_path": db_det.image_path,
            "timestamp": db_det.timestamp.isoformat(),
            "status": db_det.status,
            "event_type": db_det.event_type,
            "subtype": db_det.subtype,
            "bus_id": db_det.bus_id,
            "plate_number": db_det.plate_number,
            "plate_confidence": db_det.plate_confidence
        }
    }
    await manager.broadcast(payload)
    return {"status": "success", "detection": db_det}


# ==================== PUBLIC TRANSIT FLEET & DYNAMIC ROUTING CONFIG ==================== #

BUS_ROUTES_CONFIG = {
    "BUS-101": {
        "route_name": "Route 42A - EM Bypass Arterial (Science City - Ruby)",
        "color": "#06b6d4",
        "scheduled_waypoints": [
            [22.5726, 88.3639],  # Esplanade / Central Kolkata
            [22.5645, 88.3712],  # Sealdah Flyover Approach
            [22.5448, 88.3685],  # Park Circus 7-Point
            [22.5390, 88.3965],  # Science City / EM Bypass
            [22.5180, 88.3980],  # Ruby Hospital Crossing
            [22.4985, 88.3995]   # Kalikapur / Garia Corridor
        ],
        "hazard_segment": [
            [22.5390, 88.3965],
            [22.5180, 88.3980]
        ],
        "detour_segment": [
            [22.5448, 88.3685],  # Park Circus 7-Point (Detour branches off from original route)
            [22.5360, 88.3850],  # Topsia Diversion Feeder
            [22.5250, 88.3910],  # Anandapur Feeder Arterial
            [22.5120, 88.4010],  # Madurdaha Connector
            [22.4985, 88.3995]   # Kalikapur / Garia Corridor (Rejoining original route)
        ],
        "reroute_waypoints": [
            [22.5726, 88.3639],
            [22.5645, 88.3712],
            [22.5448, 88.3685],
            [22.5360, 88.3850],  # Topsia Diversion Feeder
            [22.5250, 88.3910],  # Anandapur Feeder Arterial
            [22.5120, 88.4010],  # Madurdaha Connector
            [22.4985, 88.3995]   # Rejoining Kalikapur / Garia Corridor
        ],
        "hazard_reason": "Critical Pothole & Cavity Cluster Detected on Science City Arterial",
        "is_rerouted": False,
        "active_road_name": "EM Bypass Arterial Corridor, Kolkata"
    },
    "BUS-104": {
        "route_name": "Route 18B - VIP Road & Salt Lake Sector V",
        "color": "#f59e0b",
        "scheduled_waypoints": [
            [22.5980, 88.3950],  # Ultadanga Junction (Start of Trip)
            [22.5940, 88.4050],  # VIP Road Approach (Original Lane - Approaching Congestion Ahead)
            [22.5930, 88.4080],  # Lake Town Crossing (Congestion Bottleneck Start - Original Lane)
            [22.5890, 88.4180],  # Lake Town Clock Tower (Congestion Bottleneck End - Original Lane)
            [22.5800, 88.4280],  # Salt Lake Gate / Kestopur
            [22.5620, 88.4350]   # Salt Lake Sector V Tech Hub
        ],
        "hazard_segment": [
            [22.5930, 88.4080],  # Lake Town VIP Road (Congestion Bottleneck Start - Original Lane)
            [22.5890, 88.4180]   # Lake Town Clock Tower (Congestion Bottleneck End - Original Lane)
        ],
        "detour_segment": [
            [22.5940, 88.4050],  # VIP Road Approach (Detour branches off from original route)
            [22.5830, 88.3980],  # HUDCO More / EM Bypass (Changed Lane Detour)
            [22.5700, 88.4080],  # Salt Lake Stadium / Broadway Feeder
            [22.5650, 88.4200],  # Central Park Salt Lake
            [22.5620, 88.4350]   # Rejoining Sector V Tech Hub
        ],
        "reroute_waypoints": [
            [22.5980, 88.3950],  # Ultadanga Junction (Start of Trip)
            [22.5940, 88.4050],  # VIP Road Approach (Facing Congestion Ahead -> Autonomous Lane Change Divergence Point)
            [22.5830, 88.3980],  # HUDCO More / EM Bypass (Changed Lane Detour)
            [22.5700, 88.4080],  # Salt Lake Stadium / Broadway Feeder
            [22.5650, 88.4200],  # Central Park Salt Lake
            [22.5620, 88.4350]   # Rejoining Sector V Tech Hub
        ],
        "hazard_reason": "Severe Traffic Congestion Bottleneck on VIP Road Original Lane (8 km/h)",
        "is_rerouted": False,
        "active_road_name": "VIP Road Corridor, Kolkata"
    }
}

def get_bus_interpolated_coord(bus_id: str, frame_num: int) -> Tuple[float, float]:
    cfg = BUS_ROUTES_CONFIG.get(bus_id)
    if not cfg:
        return (22.5726, 88.3639)
    waypoints = cfg["reroute_waypoints"] if cfg["is_rerouted"] else cfg["scheduled_waypoints"]
    if len(waypoints) < 2:
        return waypoints[0][0], waypoints[0][1]
    
    cycle_frames = 150 if bus_id == "BUS-104" else 140
    total_segments = len(waypoints) - 1
    segment_frames = cycle_frames / total_segments
    curr_frame = frame_num % cycle_frames
    
    seg_idx = min(int(curr_frame // segment_frames), total_segments - 1)
    sub_prog = (curr_frame % segment_frames) / segment_frames
    
    p1 = waypoints[seg_idx]
    p2 = waypoints[seg_idx + 1]
    lat = round(p1[0] + (p2[0] - p1[0]) * sub_prog, 6)
    lon = round(p1[1] + (p2[1] - p1[1]) * sub_prog, 6)
    return lat, lon

sim_stream_task = None
is_sim_streaming = False
active_stream_bus = "BUS-101"

def generate_road_frame(frame_num: int, width: int = 640, height: int = 480) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        ratio = y / height
        val = int(40 + ratio * 30)
        frame[y, :] = (val, val, val)

    vx, vy = width // 2, height // 3
    cv2.line(frame, (vx, vy), (30, height), (190, 190, 190), 3)
    cv2.line(frame, (vx, vy), (width - 30, height), (190, 190, 190), 3)

    speed = 15
    offset = (frame_num * speed) % 70
    for y in range(vy + offset, height, 70):
        scale = (y - vy) / float(height - vy)
        line_len = int(25 * scale)
        line_w = max(2, int(5 * scale))
        cv2.line(frame, (vx, y), (vx, min(height, y + line_len)), (255, 255, 255), line_w)
    return frame

async def continuous_sim_loop():
    global is_sim_streaming, active_stream_bus
    frame_num = 0
    severe_pothole_frames_count = 0
    traffic_congestion_frames_count = 0
    print("[Sim Loop] BEL UrbanSense Fleet Simulation STARTED!")

    # Video Sources:
    # BUS-101: Indian Highway / Potholes footage
    # BUS-104: Middle Kolkata @ Peak Hours Traffic Video (https://youtu.be/BS-hOgmtKTA)
    demo_video_path_101 = os.path.join(os.path.dirname(__file__), "static", "youtube_demo.mp4")
    if not os.path.exists(demo_video_path_101):
        demo_video_path_101 = os.path.join(os.path.dirname(__file__), "static", "real_road_demo.mp4")
    if not os.path.exists(demo_video_path_101):
        demo_video_path_101 = os.path.join(os.path.dirname(os.path.dirname(__file__)), "real_road_demo.mp4")

    demo_video_path_104 = os.path.join(os.path.dirname(__file__), "static", "bus104_traffic.mp4")
    if not os.path.exists(demo_video_path_104):
        demo_video_path_104 = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server", "static", "bus104_traffic.mp4")

    cap_101 = None
    if os.path.exists(demo_video_path_101):
        cap_101 = cv2.VideoCapture(demo_video_path_101)
        if cap_101.isOpened():
            print(f"[Sim Loop] Playing BUS-101 video: {demo_video_path_101}")

    cap_104 = None
    if os.path.exists(demo_video_path_104):
        cap_104 = cv2.VideoCapture(demo_video_path_104)
        if cap_104.isOpened():
            print(f"[Sim Loop] Playing BUS-104 video: {demo_video_path_104}")

    loop_start_time = time.time()
    bus_log_state = {
        "BUS-101": {"last_defect": 0.0, "last_congestion": 0.0, "last_anpr": 0.0, "defects": 0, "congestion": 0, "anpr": 0, "start_time": time.time()},
        "BUS-104": {"last_defect": 0.0, "last_congestion": 0.0, "last_anpr": 0.0, "defects": 0, "congestion": 0, "anpr": 0, "start_time": time.time()}
    }

    try:
        while is_sim_streaming:
            try:
                # 1. Update Bus Fleet Positions for ALL 3 routes
                active_bus = active_stream_bus
                b104_cycle_frame = frame_num % 150
                now_ts = time.time()
                is_b104_manual = (now_ts < b104_manual_override_expiry)

                # Autonomous facing-congestion lane change for BUS-104 (ONLY when streaming BUS-104!):
                if active_bus == "BUS-104" and not is_b104_manual:
                    if 28 <= b104_cycle_frame < 146:
                        if not BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"]:
                            BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] = True
                            await manager.broadcast({
                                "type": "ROUTE_REROUTE_EVENT",
                                "bus_id": "BUS-104",
                                "is_rerouted": True,
                                "rerouted": True,
                                "reason": "🚨 AUTONOMOUS LANE CHANGE ACTIVATED: Facing Heavy Traffic Congestion Queue on VIP Road Original Lane (8 km/h) — Diverting to Changed Lane (Broadway Detour • 34 km/h free flow)!",
                                "route_name": BUS_ROUTES_CONFIG["BUS-104"]["route_name"],
                                "hazard_segment": BUS_ROUTES_CONFIG["BUS-104"]["hazard_segment"],
                                "detour_route": BUS_ROUTES_CONFIG["BUS-104"]["reroute_waypoints"],
                                "detour_segment": BUS_ROUTES_CONFIG["BUS-104"]["detour_segment"],
                                "scheduled_route": BUS_ROUTES_CONFIG["BUS-104"]["scheduled_waypoints"]
                            })
                    elif b104_cycle_frame < 28:
                        if BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"]:
                            BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] = False
                            await manager.broadcast({
                                "type": "ROUTE_REROUTE_EVENT",
                                "bus_id": "BUS-104",
                                "is_rerouted": False,
                                "rerouted": False,
                                "reason": "BUS-104 Departed Ultadanga — Traveling on Original Lane (VIP Road Corridor)",
                                "route_name": BUS_ROUTES_CONFIG["BUS-104"]["route_name"],
                                "hazard_segment": BUS_ROUTES_CONFIG["BUS-104"]["hazard_segment"],
                                "detour_route": BUS_ROUTES_CONFIG["BUS-104"]["reroute_waypoints"],
                                "scheduled_route": BUS_ROUTES_CONFIG["BUS-104"]["scheduled_waypoints"]
                            })

                # Autonomous pothole-hazard detour diversion for BUS-101 (when streaming BUS-101):
                b101_cycle_frame = frame_num % 140
                if active_bus == "BUS-101":
                    # In first journey from start (Esplanade), as potholes are sensed ahead,
                    # activate dynamic detour at frame 20 so it appears at Park Circus before bus arrives!
                    if 20 <= b101_cycle_frame < 136:
                        if not BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"]:
                            BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"] = True
                            await manager.broadcast({
                                "type": "ROUTE_REROUTE_EVENT",
                                "bus_id": "BUS-101",
                                "is_rerouted": True,
                                "rerouted": True,
                                "reason": "🚨 CRITICAL HAZARD DETECTED: Severe Pothole Cluster on EM Bypass Arterial — Dynamic Route Diversion Activated via Topsia-Anandapur Bypass!",
                                "route_name": BUS_ROUTES_CONFIG["BUS-101"]["route_name"],
                                "hazard_segment": BUS_ROUTES_CONFIG["BUS-101"]["hazard_segment"],
                                "detour_route": BUS_ROUTES_CONFIG["BUS-101"]["reroute_waypoints"],
                                "detour_segment": BUS_ROUTES_CONFIG["BUS-101"]["detour_segment"],
                                "scheduled_route": BUS_ROUTES_CONFIG["BUS-101"]["scheduled_waypoints"]
                            })
                    elif b101_cycle_frame < 20:
                        if BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"]:
                            BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"] = False
                            await manager.broadcast({
                                "type": "ROUTE_REROUTE_EVENT",
                                "bus_id": "BUS-101",
                                "is_rerouted": False,
                                "rerouted": False,
                                "reason": "BUS-101 Departed Esplanade — Traveling on Scheduled Route (EM Bypass Arterial)",
                                "route_name": BUS_ROUTES_CONFIG["BUS-101"]["route_name"],
                                "hazard_segment": BUS_ROUTES_CONFIG["BUS-101"]["hazard_segment"],
                                "detour_route": BUS_ROUTES_CONFIG["BUS-101"]["reroute_waypoints"],
                                "detour_segment": BUS_ROUTES_CONFIG["BUS-101"]["detour_segment"],
                                "scheduled_route": BUS_ROUTES_CONFIG["BUS-101"]["scheduled_waypoints"]
                            })

                lat1, lon1 = get_bus_interpolated_coord("BUS-101", frame_num)
                lat2, lon2 = get_bus_interpolated_coord("BUS-104", frame_num)

                if active_bus == "BUS-104":
                    cur_lat, cur_lon = lat2, lon2
                    cur_route_name = BUS_ROUTES_CONFIG["BUS-104"]["route_name"]
                    is_bus_rerouted = BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"]
                    if is_bus_rerouted:
                        cur_road_name = "Broadway Feeder Detour (Clear Route • 34 km/h), Kolkata"
                        cur_speed = 34.0
                    else:
                        cur_road_name = "VIP Road Corridor (Lake Town Bottleneck Ahead), Kolkata"
                        if b104_cycle_frame < 22:
                            cur_speed = 28.0
                        else:
                            cur_speed = max(8.0, round(28.0 - (b104_cycle_frame - 21) * 3.0, 1))
                    gps_tracker.update_location(lat2, lon2, time.time())
                else:
                    cur_lat, cur_lon = lat1, lon1
                    cur_route_name = BUS_ROUTES_CONFIG["BUS-101"]["route_name"]
                    is_bus_rerouted = BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"]
                    if is_bus_rerouted:
                        cur_road_name = "Topsia-Anandapur Detour Bypass (Bypassing Craters • 32 km/h), Kolkata"
                        cur_speed = 32.0
                    else:
                        cur_road_name = "EM Bypass Arterial Corridor, Kolkata"
                        cur_speed = round(28.0 + (frame_num % 12), 1)
                    gps_tracker.update_location(lat1, lon1, time.time())

                # Update Fleet in DB
                db = SessionLocal()
                try:
                    bus1 = db.query(models.BusFleet).filter(models.BusFleet.id == "BUS-101").first()
                    if bus1:
                        bus1.current_lat = lat1
                        bus1.current_lon = lon1
                        bus1.speed_kmh = round(28.0 + (frame_num % 12), 1)
                        bus1.status = "rerouted" if BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"] else "on_route"

                    bus2 = db.query(models.BusFleet).filter(models.BusFleet.id == "BUS-104").first()
                    if bus2:
                        bus2.current_lat = lat2
                        bus2.current_lon = lon2
                        bus2.speed_kmh = cur_speed if active_bus == "BUS-104" else (34.0 if BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] else 18.5)
                        bus2.status = "rerouted" if BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] else "on_route"
                    db.commit()
                finally:
                    db.close()

                # 2. Get frame from active video capture
                frame = None
                if active_bus == "BUS-104":
                    if cap_104 is None or not cap_104.isOpened():
                        for p in [demo_video_path_104, os.path.join("server", "static", "bus104_traffic.mp4"), "bus104_traffic.mp4"]:
                            if os.path.exists(p):
                                cap_104 = cv2.VideoCapture(p)
                                if cap_104.isOpened():
                                    print(f"[Sim Loop] Dynamically opened BUS-104 capture: {p}")
                                    break
                    active_cap = cap_104
                else:
                    if cap_101 is None or not cap_101.isOpened():
                        for p in [demo_video_path_101, os.path.join("server", "static", "youtube_demo.mp4"), "real_road_demo.mp4"]:
                            if os.path.exists(p):
                                cap_101 = cv2.VideoCapture(p)
                                if cap_101.isOpened():
                                    break
                    active_cap = cap_101

                if active_cap is not None and active_cap.isOpened():
                    ret, raw_frame = active_cap.read()
                    if not ret or raw_frame is None:
                        active_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, raw_frame = active_cap.read()
                    if ret and raw_frame is not None:
                        frame = cv2.resize(raw_frame, (640, 480))

                if frame is None:
                    frame = generate_road_frame(frame_num)

                _, jpeg_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                frame_bytes = jpeg_buf.tobytes()

                # Support interactive camera angle or automatic rotation including Rear ANPR
                if active_camera_angle and active_camera_angle != "front":
                    camera_angle = active_camera_angle
                else:
                    # Naturally rotate: Front (0-120), Side (121-150), Rear ANPR (151-185)
                    cycle_pos = frame_num % 185
                    if cycle_pos > 150:
                        camera_angle = "rear"
                    elif cycle_pos > 120:
                        camera_angle = "side"
                    else:
                        camera_angle = "front"

                forced_event = None
                if frame_num > 0 and frame_num % 90 == 0:
                    forced_event = random.choice(["traffic_bottleneck", "missing_infrastructure", "pedestrian_safety"])

                annotated_frame_bytes, detections = detector.process_frame(
                    frame_bytes, 
                    camera_angle=camera_angle,
                    force_event_type=forced_event,
                    bus_id=active_bus
                )

                # Telemetry tracking for live HUD
                if active_bus == "BUS-104":
                    if detections and any(d.get("event_type") == "traffic_bottleneck" or d.get("subtype") == "heavy_congestion" for d in detections):
                        traffic_congestion_frames_count += 1

                # 3. Broadcast live camera feed
                b64_frame = base64.b64encode(annotated_frame_bytes).decode('utf-8')
                await manager.broadcast({
                    "type": "LIVE_FRAME",
                    "image": f"data:image/jpeg;base64,{b64_frame}",
                    "timestamp": time.time(),
                    "has_detections": len(detections) > 0,
                    "detection_subtype": detections[0].get("subtype", detections[0].get("event_type", "heavy_congestion" if active_bus == "BUS-104" else "pothole")) if detections else None,
                    "bus_id": active_bus,
                    "camera_angle": camera_angle,
                    "gps": {"lat": cur_lat, "lon": cur_lon},
                    "speed": cur_speed,
                    "is_rerouted": is_bus_rerouted,
                    "route_name": cur_route_name
                })

                # Broadcast Fleet Update every 8 frames
                if frame_num % 8 == 0:
                    await manager.broadcast({
                        "type": "FLEET_UPDATE",
                        "buses": [
                            {
                                "id": "BUS-101",
                                "lat": lat1,
                                "lon": lon1,
                                "speed": round(28.0 + (frame_num % 12), 1),
                                "delay": 1.5 + (2.5 if BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"] else 0.0),
                                "status": "rerouted" if BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"] else "on_route",
                                "is_rerouted": BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"],
                                "route_name": BUS_ROUTES_CONFIG["BUS-101"]["route_name"],
                                "scheduled_waypoints": BUS_ROUTES_CONFIG["BUS-101"]["scheduled_waypoints"],
                                "hazard_segment": BUS_ROUTES_CONFIG["BUS-101"]["hazard_segment"],
                                "reroute_waypoints": BUS_ROUTES_CONFIG["BUS-101"]["reroute_waypoints"],
                                "detour_segment": BUS_ROUTES_CONFIG["BUS-101"]["detour_segment"],
                                "hazard_reason": BUS_ROUTES_CONFIG["BUS-101"]["hazard_reason"]
                            },
                            {
                                "id": "BUS-104",
                                "lat": lat2,
                                "lon": lon2,
                                "speed": 34.0 if BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] else 18.5,
                                "delay": 2.5 if BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] else 8.5,
                                "status": "rerouted" if BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] else "delayed",
                                "is_rerouted": BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"],
                                "route_name": BUS_ROUTES_CONFIG["BUS-104"]["route_name"],
                                "scheduled_waypoints": BUS_ROUTES_CONFIG["BUS-104"]["scheduled_waypoints"],
                                "hazard_segment": BUS_ROUTES_CONFIG["BUS-104"]["hazard_segment"],
                                "reroute_waypoints": BUS_ROUTES_CONFIG["BUS-104"]["reroute_waypoints"],
                                "detour_segment": BUS_ROUTES_CONFIG["BUS-104"]["detour_segment"],
                                "hazard_reason": BUS_ROUTES_CONFIG["BUS-104"]["hazard_reason"]
                            }
                        ]
                    })

                # 4. Save detections to DB with Real-Life Edge-AI Pacing
                # (Increments figures 1, 2, 3... at natural intervals matching real-world road travel)
                now_sim = time.time()
                if active_bus not in bus_log_state:
                    bus_log_state[active_bus] = {
                        "last_defect": 0.0,
                        "last_congestion": 0.0,
                        "last_anpr": 0.0,
                        "defects": 0,
                        "congestion": 0,
                        "anpr": 0,
                        "start_time": now_sim
                    }
                b_state = bus_log_state[active_bus]
                events_to_log = []

                if active_bus == "BUS-104":
                    # BUS-104: VIP Road Corridor (Traffic Bottlenecks; NO potholes)
                    time_since_cong = now_sim - b_state["last_congestion"] if b_state["last_congestion"] > 0 else (now_sim - b_state["start_time"])
                    cong_ready = (b_state["last_congestion"] == 0.0 and time_since_cong >= 4.0) or (time_since_cong >= 14.0)

                    if cong_ready:
                        cong_candidates = [d for d in detections if d.get("event_type") == "traffic_bottleneck"]
                        cand = cong_candidates[0] if cong_candidates else {
                            "class": "traffic_bottleneck",
                            "event_type": "traffic_bottleneck",
                            "subtype": "heavy_congestion",
                            "vehicle_density": round(random.uniform(0.82, 0.89), 2),
                            "vehicle_count": random.randint(18, 28),
                            "confidence": 0.94,
                            "severity": "high",
                            "bbox": [100, 140, 540, 420],
                            "annotated_image": None
                        }
                        b_state["congestion"] += 1
                        b_state["last_congestion"] = now_sim

                        t_prog = min(0.92, 0.12 + (b_state["congestion"] * 0.20))
                        h_p1 = BUS_ROUTES_CONFIG["BUS-104"]["hazard_segment"][0]
                        h_p2 = BUS_ROUTES_CONFIG["BUS-104"]["hazard_segment"][1]
                        det_lat = round(h_p1[0] + (h_p2[0] - h_p1[0]) * t_prog + random.uniform(-0.0001, 0.0001), 6)
                        det_lon = round(h_p1[1] + (h_p2[1] - h_p1[1]) * t_prog + random.uniform(-0.0001, 0.0001), 6)

                        events_to_log.append({
                            "det": cand,
                            "lat": det_lat,
                            "lon": det_lon,
                            "road_label": "VIP Road Corridor (Lake Town Bottleneck), Kolkata",
                            "bus_id": "BUS-104",
                            "route_id": "Route-18B"
                        })

                else:
                    # BUS-101: EM Bypass Arterial (Road Potholes & Craters; NO congestion)
                    time_since_def = now_sim - b_state["last_defect"] if b_state["last_defect"] > 0 else (now_sim - b_state["start_time"])
                    defect_ready = (b_state["last_defect"] == 0.0 and time_since_def >= 1.2) or (time_since_def >= 5.0)

                    if defect_ready:
                        defect_candidates = [d for d in detections if d.get("event_type") == "road_defect"]
                        if defect_candidates:
                            defect_candidates.sort(key=lambda d: d.get("confidence", 0.0), reverse=True)
                            cand = defect_candidates[0]
                        else:
                            cand = {
                                "class": "pothole",
                                "event_type": "road_defect",
                                "subtype": "pothole",
                                "confidence": round(random.uniform(0.88, 0.96), 2),
                                "severity": "high",
                                "bbox": [140, 220, 480, 420],
                                "annotated_image": None
                            }

                        b_state["defects"] += 1
                        b_state["last_defect"] = now_sim

                        t_prog = min(0.92, 0.15 + ((b_state["defects"] % 5) * 0.18))
                        h_p1 = BUS_ROUTES_CONFIG["BUS-101"]["hazard_segment"][0]
                        h_p2 = BUS_ROUTES_CONFIG["BUS-101"]["hazard_segment"][1]
                        det_lat = round(h_p1[0] + (h_p2[0] - h_p1[0]) * t_prog + random.uniform(-0.0001, 0.0001), 6)
                        det_lon = round(h_p1[1] + (h_p2[1] - h_p1[1]) * t_prog + random.uniform(-0.0001, 0.0001), 6)

                        events_to_log.append({
                            "det": cand,
                            "lat": det_lat,
                            "lon": det_lon,
                            "road_label": "EM Bypass Arterial (Hazard Crater Zone), Kolkata",
                            "bus_id": "BUS-101",
                            "route_id": "Route-42A"
                        })

                        # Promptly activate dynamic route diversion detour upon sensing potholes on the corridor!
                        if not BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"]:
                            BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"] = True
                            await manager.broadcast({
                                "type": "ROUTE_REROUTE_EVENT",
                                "bus_id": "BUS-101",
                                "is_rerouted": True,
                                "rerouted": True,
                                "reason": "CRITICAL HAZARD DETECTED: Severe Pothole Cluster on Primary Arterial — Dynamic Route Diversion Activated via Secondary Feeder Road",
                                "route_name": BUS_ROUTES_CONFIG["BUS-101"]["route_name"],
                                "hazard_segment": BUS_ROUTES_CONFIG["BUS-101"]["hazard_segment"],
                                "detour_route": BUS_ROUTES_CONFIG["BUS-101"]["reroute_waypoints"],
                                "detour_segment": BUS_ROUTES_CONFIG["BUS-101"]["detour_segment"],
                                "scheduled_route": BUS_ROUTES_CONFIG["BUS-101"]["scheduled_waypoints"]
                            })

                # ANPR Offending Vehicles: Log violation every ~24 to 32 seconds
                time_since_anpr = now_sim - b_state["last_anpr"] if b_state["last_anpr"] > 0 else (now_sim - b_state["start_time"])
                anpr_ready = (b_state["last_anpr"] == 0.0 and time_since_anpr >= 18.0) or (time_since_anpr >= 26.0)

                if anpr_ready:
                    anpr_candidates = [d for d in detections if d.get("event_type") == "offending_vehicle" or d.get("plate_number")]
                    if anpr_candidates:
                        cand = anpr_candidates[0]
                        b_state["anpr"] += 1
                        b_state["last_anpr"] = now_sim
                        events_to_log.append({
                            "det": cand,
                            "lat": cur_lat + random.uniform(-0.0002, 0.0002),
                            "lon": cur_lon + random.uniform(-0.0002, 0.0002),
                            "road_label": cur_road_name,
                            "bus_id": active_bus,
                            "route_id": "Route-18B" if active_bus == "BUS-104" else "Route-42A"
                        })

                bus_log_state[active_bus] = b_state

                # Save the throttled, real-life events to DB & broadcast
                if events_to_log:
                    db = SessionLocal()
                    try:
                        for item in events_to_log:
                            det = item["det"]
                            det_lat = item["lat"]
                            det_lon = item["lon"]
                            road_label = item["road_label"]
                            bus_target_id = item["bus_id"]
                            route_target_id = item["route_id"]

                            curr_dt = datetime.utcnow()
                            snap_bytes = det.get("annotated_image")
                            if not snap_bytes:
                                _, enc = cv2.imencode('.jpg', frame)
                                snap_bytes = enc.tobytes()

                            filename = f"sim_{uuid.uuid4().hex[:8]}_{int(time.time())}.jpg"
                            filepath = os.path.join(UPLOADS_DIR, filename)
                            with open(filepath, "wb") as f:
                                f.write(snap_bytes)

                            rel_image_path = f"/static/uploads/{filename}"
                            db_det = models.Detection(
                                lat=det_lat,
                                lon=det_lon,
                                severity=det.get("severity", "medium"),
                                confidence=det.get("confidence", 0.85),
                                image_path=rel_image_path,
                                timestamp=curr_dt,
                                status="reported",
                                event_type=det.get("event_type", "road_defect"),
                                subtype=det.get("subtype", "pothole"),
                                bus_id=bus_target_id,
                                route_id=route_target_id,
                                camera_angle=camera_angle,
                                road_name=road_label,
                                vehicle_density=det.get("vehicle_density", 0.0),
                                vehicle_count=det.get("vehicle_count", 0),
                                plate_number=det.get("plate_number"),
                                plate_confidence=det.get("plate_confidence", 0.0),
                                session_id="sim_video",
                                bbox=json.dumps(det.get("bbox", [0, 0, 0, 0]))
                            )
                            db.add(db_det)
                            db.commit()
                            db.refresh(db_det)

                            if db_det.plate_number:
                                print(f"[BACKEND-AI] [!] ANPR OFFENSE (#{b_state['anpr']}): Plate={db_det.plate_number} | Offense={db_det.subtype} | Bus={db_det.bus_id}", flush=True)
                            elif db_det.event_type == "traffic_bottleneck":
                                print(f"[BACKEND-AI] [*] TRAFFIC BOTTLENECK (#{b_state['congestion']}): Queue={db_det.vehicle_count} vehicles | Density={int(db_det.vehicle_density*100)}% | Bus={db_det.bus_id}", flush=True)
                            else:
                                print(f"[BACKEND-AI] [+] ROAD HAZARD (#{b_state['defects']}): {db_det.subtype.upper()} | Conf={int(db_det.confidence*100)}% | Bus={db_det.bus_id}", flush=True)

                            await manager.broadcast({
                                "type": "NEW_DETECTION",
                                "detection": {
                                    "id": db_det.id,
                                    "lat": db_det.lat,
                                    "lon": db_det.lon,
                                    "severity": db_det.severity,
                                    "confidence": db_det.confidence,
                                    "image_path": db_det.image_path,
                                    "timestamp": db_det.timestamp.isoformat(),
                                    "status": db_det.status,
                                    "event_type": db_det.event_type,
                                    "subtype": db_det.subtype,
                                    "bus_id": db_det.bus_id,
                                    "road_name": db_det.road_name,
                                    "plate_number": db_det.plate_number,
                                    "plate_confidence": db_det.plate_confidence
                                }
                            })
                    finally:
                        db.close()

                frame_num += 1
                await asyncio.sleep(0.12)  # ~8 FPS smooth video playback
            except Exception as frame_err:
                print(f"[Sim Loop] Frame error: {frame_err}")
                await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[Sim Loop] Error: {e}")
    finally:
        if cap_101 is not None:
            cap_101.release()
        if cap_104 is not None:
            cap_104.release()
        print("[Sim Loop] Released video captures.")

def math_sin_offset(frame: int, scale: float) -> float:
    import math
    return math.sin(frame * 0.05) * scale

def math_cos_offset(frame: int, scale: float) -> float:
    import math
    return math.cos(frame * 0.05) * scale

@app.on_event("startup")
async def startup_fleet_simulation():
    global is_sim_streaming, sim_stream_task
    is_sim_streaming = False
    print("[Startup] BEL UrbanSense ready in Standby. Waiting for user to open video stream.")

@app.post("/api/sim/stream/start")
async def start_sim_stream(bus_id: str = Query("BUS-101")):
    global is_sim_streaming, sim_stream_task, active_stream_bus
    if bus_id and bus_id in BUS_ROUTES_CONFIG:
        active_stream_bus = bus_id
        BUS_ROUTES_CONFIG["BUS-101"]["is_rerouted"] = False
        BUS_ROUTES_CONFIG["BUS-104"]["is_rerouted"] = False
        print(f"[Sim Stream Start] Active stream bus set to: {active_stream_bus}")
    if sim_stream_task and not sim_stream_task.done():
        sim_stream_task.cancel()
        try:
            await sim_stream_task
        except asyncio.CancelledError:
            pass
        sim_stream_task = None
    is_sim_streaming = True
    sim_stream_task = asyncio.create_task(continuous_sim_loop())
    return {"status": "started", "streaming": True, "active_bus": active_stream_bus}

@app.post("/api/sim/stream/stop")
async def stop_sim_stream():
    global is_sim_streaming, sim_stream_task
    is_sim_streaming = False
    if sim_stream_task:
        sim_stream_task.cancel()
        sim_stream_task = None
    print("[Sim Loop] Video stream stopped (Standby).")
    return {"status": "stopped", "streaming": False, "active_bus": active_stream_bus}

@app.post("/api/sim/stream/toggle")
async def toggle_sim_stream(bus_id: Optional[str] = Query(None)):
    global is_sim_streaming, sim_stream_task, active_stream_bus
    if bus_id and bus_id in BUS_ROUTES_CONFIG:
        active_stream_bus = bus_id
        print(f"[Sim Stream Toggle] Active stream bus set to: {active_stream_bus}")
    is_sim_streaming = not is_sim_streaming
    if is_sim_streaming:
        if sim_stream_task and not sim_stream_task.done():
            sim_stream_task.cancel()
            try:
                await sim_stream_task
            except asyncio.CancelledError:
                pass
            sim_stream_task = None
        sim_stream_task = asyncio.create_task(continuous_sim_loop())
        return {"status": "started", "streaming": True, "active_bus": active_stream_bus}
    else:
        if sim_stream_task:
            sim_stream_task.cancel()
            sim_stream_task = None
        print("[Sim Loop] Continuous simulation STOPPED.")
        return {"status": "stopped", "streaming": False, "active_bus": active_stream_bus}

@app.get("/api/sim/stream/status")
def get_sim_stream_status():
    return {"streaming": is_sim_streaming, "active_bus": active_stream_bus}

active_camera_angle = "front"

@app.post("/api/sim/camera_angle")
async def set_sim_camera_angle(angle: str = Query("front")):
    global active_camera_angle
    active_camera_angle = angle
    print(f"[Sim] Active camera angle switched to: {active_camera_angle}")
    return {"status": "success", "camera_angle": active_camera_angle}

@app.post("/api/sim/select_bus")
async def select_sim_bus(bus_id: str = Query("BUS-101")):
    global active_stream_bus
    if bus_id in BUS_ROUTES_CONFIG:
        active_stream_bus = bus_id
        print(f"[Sim Loop] Active camera bus switched to: {active_stream_bus}")
        return {"status": "success", "active_bus": active_stream_bus}
    raise HTTPException(status_code=400, detail="Invalid bus_id")

@app.get("/api/sim/active_bus")
def get_active_sim_bus():
    return {"active_bus": active_stream_bus}

