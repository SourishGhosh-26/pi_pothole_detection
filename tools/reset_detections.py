import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "server", "patchsense.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("DELETE FROM detections")
try:
    c.execute("DELETE FROM sqlite_sequence WHERE name='detections'")
except Exception as e:
    print(f"sqlite_sequence note: {e}")
conn.commit()
c.execute("SELECT COUNT(*) FROM detections")
count = c.fetchone()[0]
print(f"[DB RESET] Current detections count in DB: {count}")
conn.close()
