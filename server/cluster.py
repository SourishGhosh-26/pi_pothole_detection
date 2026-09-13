import math
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import models

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in meters between two points 
    on the earth (specified in decimal degrees).
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c

def is_duplicate_detection(
    db: Session, 
    lat: float, 
    lon: float, 
    timestamp: datetime, 
    max_distance_meters: float = 15.0, 
    max_time_seconds: float = 60.0,
    event_type: str = "road_defect",
    plate_number: Optional[str] = None
) -> bool:
    """
    Checks if a detection at (lat, lon) at timestamp is within max_distance_meters
    and max_time_seconds of an existing detection in the database.
    Prevents duplicate road defects while allowing distinct ANPR vehicle detections.
    """
    recent_detections = db.query(models.Detection).order_by(models.Detection.timestamp.desc()).limit(100).all()
    
    for det in recent_detections:
        # If checking for ANPR license plate deduplication:
        if plate_number:
            if det.plate_number and det.plate_number == plate_number:
                time_diff = abs((timestamp - det.timestamp).total_seconds())
                if time_diff <= max_time_seconds:
                    return True
            continue

        # If different event types (e.g. road_defect vs offending_vehicle), they are not duplicates
        if det.event_type != event_type:
            continue

        time_diff = abs((timestamp - det.timestamp).total_seconds())
        if time_diff <= max_time_seconds:
            dist = haversine_distance(lat, lon, det.lat, det.lon)
            if dist <= max_distance_meters:
                return True
    return False
