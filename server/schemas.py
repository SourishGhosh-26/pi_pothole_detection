from pydantic import BaseModel
from typing import Optional, List
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
    session_id: Optional[str] = "default"
    bbox: Optional[str] = None

class DetectionCreate(DetectionBase):
    pass

class DetectionUpdateStatus(BaseModel):
    status: str

class DetectionResponse(DetectionBase):
    id: int
    timestamp: datetime

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
