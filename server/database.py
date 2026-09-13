import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "patchsense.db"))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(detections)")
        existing_cols = {row[1] for row in cur.fetchall()}

        new_cols = [
            ("event_type", "TEXT DEFAULT 'road_defect'"),
            ("subtype", "TEXT DEFAULT 'pothole'"),
            ("bus_id", "TEXT DEFAULT 'BUS-101'"),
            ("route_id", "TEXT DEFAULT 'Route-42A'"),
            ("camera_angle", "TEXT DEFAULT 'front'"),
            ("road_name", "TEXT DEFAULT 'Urban Arterial Road'"),
            ("vehicle_density", "REAL DEFAULT 0.0"),
            ("vehicle_count", "INTEGER DEFAULT 0"),
            ("plate_number", "TEXT"),
            ("plate_confidence", "REAL DEFAULT 0.0"),
            ("metadata_json", "TEXT")
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE detections ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database] Migration note: {e}")
