import os
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_system():
    print("--- 1. Testing Root Endpoint ---")
    res = client.get("/")
    assert res.status_code == 200
    print("Root output:", res.json())

    print("\n--- 2. Testing Stats Endpoint (Empty DB) ---")
    res = client.get("/api/stats")
    assert res.status_code == 200
    print("Stats output:", res.json())

    print("\n--- 3. Testing Trigger Simulated Detection ---")
    res = client.post("/api/sim/trigger?lat=19.0760&lon=72.8777&severity=high")
    assert res.status_code == 200
    sim_data = res.json()
    print("Simulated detection created:", sim_data["detection"])

    print("\n--- 4. Testing Get Detections ---")
    res = client.get("/api/detections")
    assert res.status_code == 200
    detections = res.json()
    print(f"Total detections returned: {len(detections)}")

    det_id = detections[0]["id"]
    print(f"\n--- 5. Testing Update Status for Detection #{det_id} ---")
    res = client.patch(f"/api/detections/{det_id}/status", json={"status": "verified"})
    assert res.status_code == 200
    print("Updated detection:", res.json())

    print("\n--- 6. Testing Stats Endpoint After Creation ---")
    res = client.get("/api/stats")
    assert res.status_code == 200
    print("Updated Stats:", res.json())

    print("\n[SUCCESS] All server unit & API integration tests passed cleanly!")

if __name__ == "__main__":
    test_system()
