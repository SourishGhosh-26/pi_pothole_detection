import time
import threading
from typing import Optional, Dict, Tuple

class GPSTracker:
    def __init__(self, max_points: int = 200, max_age_seconds: float = 300.0):
        self.max_points = max_points
        self.max_age_seconds = max_age_seconds
        self.points = []  # List of tuples: (epoch_timestamp, lat, lon)
        self.lock = threading.Lock()
        # Fallback default location (e.g., San Francisco / Mumbai / Delhi center depending on user)
        self.default_location = (19.0760, 72.8777)  # Default Mumbai coordinates

    def update_location(self, lat: float, lon: float, timestamp: Optional[float] = None):
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.points.append((timestamp, lat, lon))
            # Sort by timestamp
            self.points.sort(key=lambda x: x[0])
            # Trim buffer
            if len(self.points) > self.max_points:
                self.points = self.points[-self.max_points:]
            
            # Update default location to latest valid ping
            self.default_location = (lat, lon)

    def get_nearest_location(self, target_timestamp: float) -> Tuple[float, float, float]:
        """
        Finds the nearest-timestamp GPS reading to target_timestamp.
        Returns (lat, lon, time_difference_seconds).
        """
        with self.lock:
            if not self.points:
                return self.default_location[0], self.default_location[1], 999.0

            # Prune points older than max_age_seconds from target_timestamp
            valid_points = [p for p in self.points if abs(target_timestamp - p[0]) <= self.max_age_seconds]
            if not valid_points:
                # Return latest known point
                latest = self.points[-1]
                return latest[1], latest[2], abs(target_timestamp - latest[0])

            # Find closest point in time
            best_point = min(valid_points, key=lambda p: abs(target_timestamp - p[0]))
            time_diff = abs(target_timestamp - best_point[0])
            return best_point[1], best_point[2], time_diff

    def get_latest_location(self) -> Tuple[float, float]:
        with self.lock:
            if not self.points:
                return self.default_location
            latest = self.points[-1]
            return latest[1], latest[2]

gps_tracker = GPSTracker()
