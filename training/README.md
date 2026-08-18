# PATCHSENSE YOLO Training Guide (Google Colab)

Run this workflow in Google Colab (with **T4 GPU** enabled) to train the custom single-class `pothole` detection model.

---

### Step 1: Install Dependencies
```python
!pip install ultralytics roboflow
```

### Step 2: Download Pothole Dataset from Roboflow
```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")

# Example using public pothole dataset (e.g. BharatPothole or pothole-detection)
project = rf.workspace("vishwajeet-patil-evpvg").project("pothole-detection-system-v1")
dataset = project.version(1).download("yolov8")

# Ensure dataset/data.yaml has:
# nc: 1
# names: ['pothole']
```

### Step 3: Train Single-Class Model (YOLO26n / YOLOv8n)
```python
from ultralytics import YOLO

# Load base nano model
model = YOLO("yolo26n.pt")  # or "yolov8n.pt"

# Train model for 50 epochs with early stopping patience=10
results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    patience=10,
    project="patchsense_runs",
    name="pothole_yolo26n"
)
```

### Step 4: Download Weights and Deploy to Laptop Server
After training completes, download `best.pt`:
```python
from google.colab import files
files.download("patchsense_runs/pothole_yolo26n/weights/best.pt")
```

Place the downloaded `best.pt` into `server/models/best.pt` on your laptop.

Restart the FastAPI server — it will automatically detect and load `server/models/best.pt` instead of the stub detector!
