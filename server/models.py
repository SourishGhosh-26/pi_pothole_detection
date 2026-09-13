from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from datetime import datetime
from database import Base

class Detection(Base):
    """
    Unified Urban Event & Defect Record
    Covers Road Defects, Traffic Density, Pedestrian Safety, and ANPR Incident Tracking.
    """
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lat = Column(Float, nullable=False, index=True)
    lon = Column(Float, nullable=False, index=True)
    severity = Column(String, nullable=False, default="medium")  # high, medium, low
    confidence = Column(Float, nullable=False, default=0.0)
    image_path = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, nullable=False, default="reported")  # reported, verified, fixed, dispatched

    # BEL Urban Platform Multi-Modal Attributes
    event_type = Column(String, nullable=False, default="road_defect")  
    # Types: "road_defect", "traffic_bottleneck", "pedestrian_safety", "offending_vehicle"

    subtype = Column(String, nullable=False, default="pothole")
    # Subtypes:
    # Road defects: "pothole", "damaged_road", "waterlogging", "missing_divider", "missing_zebra_crossing", "damaged_signboard"
    # Traffic: "heavy_congestion", "traffic_bottleneck"
    # Pedestrian: "pedestrian_in_roadway", "school_children_crossing"
    # Offending Vehicle: "rash_driving", "hit_and_run"

    bus_id = Column(String, nullable=True, default="BUS-101")
    route_id = Column(String, nullable=True, default="Route-42A")
    camera_angle = Column(String, nullable=True, default="front")  # front, side, rear
    road_name = Column(String, nullable=True, default="Urban Arterial Road")

    # Traffic Flow Analytics
    vehicle_density = Column(Float, nullable=True, default=0.0)
    vehicle_count = Column(Integer, nullable=True, default=0)

    # ANPR (Automatic Number Plate Recognition) for Offending Vehicles
    plate_number = Column(String, nullable=True)  # e.g. "AP 29 TA 6828"
    plate_confidence = Column(Float, nullable=True, default=0.0)

    # Legacy & geometry fields
    session_id = Column(String, nullable=True, default="default")
    bbox = Column(String, nullable=True)  # Store JSON string of [x1, y1, x2, y2]
    metadata_json = Column(Text, nullable=True)


class BusFleet(Base):
    """
    Public Transport Fleet Telemetry Tracker
    """
    __tablename__ = "bus_fleet"

    id = Column(String, primary_key=True, index=True)  # e.g. "BUS-101"
    route_name = Column(String, nullable=False)        # e.g. "Route 42A - Metro Corridor"
    current_lat = Column(Float, nullable=False)
    current_lon = Column(Float, nullable=False)
    speed_kmh = Column(Float, nullable=False, default=32.5)
    route_delay_min = Column(Float, nullable=False, default=2.0)
    passenger_load = Column(String, nullable=False, default="Moderate")  # Low, Moderate, High, Crowded
    status = Column(String, nullable=False, default="on_route")          # on_route, delayed, incident_alert
    active_cameras = Column(String, nullable=False, default="front,side,rear")
    last_update = Column(DateTime, default=datetime.utcnow)
