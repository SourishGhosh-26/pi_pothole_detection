# BEL UrbanSense — Autonomous Edge-AI Transit Perception & Dynamic Route Optimization System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8.svg)](https://opencv.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-GIS%20Mapping-199900.svg)](https://leafletjs.com/)

**BEL UrbanSense** is a comprehensive, real-time edge-AI urban road perception and public transit optimization system. Designed for smart cities and public transit fleets, it transforms transit buses and mobile devices into connected edge nodes that autonomously detect road hazards, monitor pedestrian safety, identify traffic congestion bottlenecks, read offending vehicle license plates (ANPR), and dynamically reroute transit vehicles to avoid hazards in real time.

---

## 👥 Project Lead & Author

- **Sourish Ghosh** ([@SourishGhosh-26](https://github.com/SourishGhosh-26)) — *Lead Developer, Edge-AI System Integration & Dynamic Routing Architecture*

---

## 🌟 Key Capabilities & Features

### 1. Autonomous Multi-Hazard Road Perception (Zero Clicks Required)
The multi-spectral computer vision engine autonomously classifies 6 critical urban road conditions with high precision without requiring any user input or button clicks:
- 🚸 **Pedestrian Safety**: Detects pedestrians, crosswalks, and school children with upright contour aspect analysis ($H/W \ge 1.50$).
- 🚦 **Traffic Congestion Bottlenecks**: Analyzes vehicle density, queue lengths, and slow crawling speeds ($<10\text{ km/h}$) to detect bottlenecks.
- 🕳️ **Severe Potholes & Craters**: Identifies asphalt surface depressions, fissures, and cavity clusters.
- 🌊 **Waterlogged Roads**: Senses surface water accumulation and specular road gloss.
- 🚧 **Missing & Damaged Infrastructure**: Flags missing dividers, damaged signboards, and worn zebra markings for PWD maintenance.
- 🚨 **Automatic Number Plate Recognition (ANPR)**: Reads vehicle license plates and logs hit-and-run, reckless driving, and illegal overtakes.

### 2. Autonomous Transit Fleet Monitoring & Dynamic Route Detours
- **Live Fleet Tracking**: Real-time GPS tracking of Kolkata transit routes (Route 42A EM Bypass and Route 18B VIP Road).
- **Dynamic Detour Activation**:
  - **BUS-101 (Hazard Avoidance)**: When potholes and craters are detected on the EM Bypass corridor, the bus autonomously branches at **Park Circus 7-Point** onto a clear green detour (Topsia ➔ Anandapur ➔ Madurdaha) and re-joins the terminus safely.
  - **BUS-104 (Congestion Bypass)**: When heavy congestion queues form on the VIP Road original lane, the bus switches to the changed lane (Broadway Detour • 34 km/h free flow).
- **Clean Map Visualization**: Shows solid scheduled lines, yellow traffic congestion circles, and green dashed detours with zero map clutter.

### 3. Smartphone & Edge-Device Integration
- **Smartphone Live Camera Node**: Any mobile phone (Android / iOS) functions as an intelligent vehicle camera node streaming real-time video and GPS coordinates over secure HTTPS (`https://<LAN_IP>:8443/camera`).
- **Vehicle Dashcam & Webcams**: Seamlessly connects to vehicle-mounted smartphone mounts, USB webcams, or pre-recorded transit camera feeds.
- **Laptop Command Center**: Dark-themed GIS operations dashboard running on `http://localhost:8000/` with WebSocket live telemetry.

---

## 🏗 System Architecture

```
   [ Smartphone Camera (HTTPS) / Vehicle Dashcam / Mobile Node ]
                              │
                              ▼ (WebSocket / Secure HTTPS Stream)
                   ┌───────────────────────┐
                   │   FastAPI Server      │
                   │   Port 8000 & 8443    │
                   └──────────┬────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
   [ Edge-AI Perception ]         [ GIS Fleet Routing Engine ]
   • Pedestrian Safety            • Real-time Bus GPS Tracking
   • Traffic Congestion           • Hazard Segment Evaluation
   • Road Defect / Pothole        • Dynamic Detour Branching
   • Automatic ANPR Reader        • Speed & Delay Optimization
               │                             │
               └──────────────┬──────────────┘
                              │
                              ▼ (WebSocket Broadcast)
           ┌──────────────────────────────────────┐
           │   BEL UrbanSense Operations Center   │
           │   (Interactive Dark-Mode GIS Map)    │
           └──────────────────────────────────────┘
```

---

## 🚀 1-Click Quick Start (For Windows)

Clone the repository:
```bash
git clone https://github.com/SourishGhosh-26/pi_pothole_detection.git
cd pi_pothole_detection
```

### Option A: Complete 1-Click Setup & Launch (Recommended)
Simply double-click:
```text
SETUP_NEW_LAPTOP.bat
```
This script automatically checks Python, creates the isolated virtual environment, installs all dependencies, generates SSL certificates, and launches the entire system!

### Option B: Quick Launch (When Already Setup)
Double-click:
```text
RUN_URBANSENSE.bat
```

### Accessing the Interfaces:
- **Laptop Command Dashboard**: Open `http://localhost:8000/` in your browser.
- **Mobile Phone Camera**: Open `https://<YOUR_LAPTOP_IP>:8443/camera` on your smartphone browser.

---

## 📁 Repository Structure

```text
├── server/
│   ├── main.py              # Central FastAPI server, WebSocket hub & fleet simulator
│   ├── detector.py          # Edge-AI multi-hazard computer vision classifier
│   ├── models.py            # SQLite database models for incident persistence
│   ├── run_server.py        # Dual HTTP/HTTPS server launcher
│   └── static/
│       ├── dashboard.html   # Mission Control GIS mapping dashboard
│       └── camera.html      # Mobile phone camera edge streaming app
├── phone_app_streamer.py    # Mobile smartphone camera edge client
├── video_streamer.py        # Video feed stream transmitter
├── tools/
│   ├── create_share_zip.py  # Generates distributable standalone project archive
│   └── reset_detections.py  # Clears database for clean demo presentation
├── SETUP_NEW_LAPTOP.bat     # Automated setup script for new machines
├── RUN_URBANSENSE.bat       # Quick launcher script
└── walkthrough.md           # Engineering verification & benchmarks
```

---

## 📄 License & Attribution

Developed by **Sourish Ghosh** for the Smart India Hackathon (SIH) BEL UrbanSense Initiative.
Licensed under the [MIT License](LICENSE).
