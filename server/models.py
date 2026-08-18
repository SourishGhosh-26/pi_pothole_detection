from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from database import Base

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lat = Column(Float, nullable=False, index=True)
    lon = Column(Float, nullable=False, index=True)
    severity = Column(String, nullable=False, default="medium")  # high, medium, low
    confidence = Column(Float, nullable=False, default=0.0)
    image_path = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, nullable=False, default="reported")  # reported, verified, fixed
    session_id = Column(String, nullable=True, default="default")
    bbox = Column(String, nullable=True)  # Store JSON string of [x1, y1, x2, y2]
