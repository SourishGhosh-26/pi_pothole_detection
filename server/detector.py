import os
import random
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, List, Dict, Any, Tuple

class PotholeDetector:
    def __init__(self, model_path: Optional[str] = None):
        self.use_stub = True
        self.model = None

        # Check for model path or default locations
        possible_paths = [
            model_path,
            os.path.join(os.path.dirname(__file__), "models", "best.pt"),
            os.path.join(os.path.dirname(__file__), "models", "yolo26n.pt"),
            os.path.join(os.path.dirname(__file__), "models", "yolov8n.pt")
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                try:
                    from ultralytics import YOLO
                    print(f"[Detector] Loading Ultralytics YOLO model from {path}...")
                    self.model = YOLO(path)
                    self.use_stub = False
                    print(f"[Detector] Successfully loaded YOLO model from {path}")
                    break
                except Exception as e:
                    print(f"[Detector] Failed to load model from {path}: {e}")

        if self.use_stub:
            print("[Detector] No valid trained YOLO model found. Using STUB detector (~30% simulated pothole detection rate).")

    def set_stub_mode(self, enabled: bool):
        self.use_stub = enabled
        print(f"[Detector] Stub mode set to: {self.use_stub}")

    def process_frame(self, image_bytes: bytes) -> Tuple[bytes, List[Dict[str, Any]]]:
        """
        Processes a raw JPEG frame.
        Draws bounding box(es) and confidence labels if potholes detected.
        Returns (annotated_jpeg_bytes, detections_list).
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, []

        h, w, _ = img.shape
        annotated_img = img.copy()

        if not self.use_stub and self.model is not None:
            detections, annotated_img = self._detect_yolo_frame(img, annotated_img, h, w)
        else:
            detections, annotated_img = self._detect_stub_frame(img, annotated_img, h, w)

        _, encoded = cv2.imencode('.jpg', annotated_img)
        return encoded.tobytes(), detections

    def detect(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        _, detections = self.process_frame(image_bytes)
        return detections

    def _detect_yolo_frame(self, img: np.ndarray, annotated_img: np.ndarray, h: int, w: int) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        results = self.model(img, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            for box in boxes:
                conf = float(box.conf[0].item())
                if conf < 0.40:
                    continue

                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                area_ratio = ((x2 - x1) * (y2 - y1)) / float(w * h)
                severity = self._calculate_severity(area_ratio, conf)

                # Draw bounding box on annotated frame (Red/Amber/Emerald)
                color = (0, 0, 255) if severity == "high" else ((0, 165, 255) if severity == "medium" else (0, 255, 0))
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)
                label = f"Pothole {conf:.2f} ({severity.upper()})"
                cv2.putText(annotated_img, label, (x1, max(y1 - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                # Encode individual snapshot for saving
                _, encoded_snap = cv2.imencode('.jpg', annotated_img)
                detections.append({
                    "class": "pothole",
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                    "severity": severity,
                    "annotated_image": encoded_snap.tobytes()
                })

        return detections, annotated_img

    def _detect_stub_frame(self, img: np.ndarray, annotated_img: np.ndarray, h: int, w: int) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        # 30% chance of detecting a pothole
        if random.random() > 0.30:
            return [], annotated_img

        box_w = random.randint(int(w * 0.2), int(w * 0.5))
        box_h = random.randint(int(h * 0.15), int(h * 0.35))
        x1 = random.randint(int(w * 0.1), max(int(w * 0.8) - box_w, int(w * 0.1) + 1))
        y1 = random.randint(int(h * 0.4), max(int(h * 0.8) - box_h, int(h * 0.4) + 1))
        x2 = x1 + box_w
        y2 = y1 + box_h

        conf = round(random.uniform(0.65, 0.98), 2)
        area_ratio = ((x2 - x1) * (y2 - y1)) / float(w * h)
        severity = self._calculate_severity(area_ratio, conf)

        color = (0, 0, 239) if severity == "high" else ((0, 191, 255) if severity == "medium" else (128, 255, 0))
        
        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)
        label = f"Pothole [STUB] {conf:.2f} ({severity.upper()})"
        cv2.putText(annotated_img, label, (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        _, encoded_snap = cv2.imencode('.jpg', annotated_img)

        detections = [{
            "class": "pothole",
            "confidence": conf,
            "bbox": [x1, y1, x2, y2],
            "severity": severity,
            "annotated_image": encoded_snap.tobytes()
        }]

        return detections, annotated_img

    def _calculate_severity(self, area_ratio: float, conf: float) -> str:
        if area_ratio >= 0.08 or conf >= 0.85:
            return "high"
        elif area_ratio >= 0.03 or conf >= 0.70:
            return "medium"
        else:
            return "low"

detector = PotholeDetector()
