from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class GPSPoint(BaseModel):
    lat: float
    lon: float
    timestamp: float  # Epoch timestamp in seconds

class DetectionBase(BaseModel):
    lat: float
    lon: float
    severity: str
    confidence: float
    image_path: str
    status: str
    event_type: Optional[str] = "road_defect"
    subtype: Optional[str] = "pothole"
    bus_id: Optional[str] = "BUS-101"
    route_id: Optional[str] = "Route-42A"
    camera_angle: Optional[str] = "front"
    road_name: Optional[str] = "Urban Arterial Road"
    vehicle_density: Optional[float] = 0.0
    vehicle_count: Optional[int] = 0
    plate_number: Optional[str] = None
    plate_confidence: Optional[float] = 0.0
    session_id: Optional[str] = "default"
    bbox: Optional[str] = None
    metadata_json: Optional[str] = None

class DetectionCreate(DetectionBase):
    pass

class DetectionUpdateStatus(BaseModel):
    status: str

class DetectionResponse(DetectionBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class BusFleetResponse(BaseModel):
    id: str
    route_name: str
    current_lat: float
    current_lon: float
    speed_kmh: float
    route_delay_min: float
    passenger_load: str
    status: str
    active_cameras: str
    last_update: datetime
    is_rerouted: Optional[bool] = False
    hazard_reason: Optional[str] = None
    scheduled_waypoints: Optional[List[List[float]]] = None
    hazard_segment: Optional[List[List[float]]] = None
    reroute_waypoints: Optional[List[List[float]]] = None
    detour_segment: Optional[List[List[float]]] = None

    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total: int
    needs_verification: int
    verified: int
    fixed: int
    high_severity: int
    medium_severity: int
    low_severity: int
    # Extended Urban KPIs
    total_road_defects: int
    total_congestion_zones: int
    total_pedestrian_risks: int
    total_offending_vehicles: int
    active_buses: int
    avg_fleet_delay_min: float
