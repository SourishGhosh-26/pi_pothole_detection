import os
import glob

def run_cleanup():
    freed_bytes = 0
    deleted_count = 0

    def safe_remove(path):
        nonlocal freed_bytes, deleted_count
        if os.path.exists(path):
            try:
                size = os.path.getsize(path)
                os.remove(path)
                freed_bytes += size
                deleted_count += 1
            except Exception as e:
                print(f"Error removing {path}: {e}")

    print("=" * 65)
    print(" [*] Cleaning up unnecessary temporary & test files...")
    print("=" * 65)

    # 1. Accidental typo & 0-byte files in root
    typo_files = ["Tap", "'Proceed", "urban_sense.db"]
    for f in typo_files:
        safe_remove(f)

    # 2. Loose test images in the root directory (45+ files)
    root_patterns = [
        "frame_*.jpg", "real_road_f*.jpg", "yt_sample_*.jpg", "yt_frame_*.jpg",
        "annotated_yt_sample_*.jpg", "bus_lane_*.jpg", "test_lc_frame*.jpg",
        "test_exact_horizon.jpg", "test_lanes_blend.jpg", "test_bottleneck_comp.jpg",
        "test_perfect_tempo_box.jpg", "test_warped_lane_change.jpg", "test_vehicle_asset.png",
        "annotated_sample.jpg", "frame_real_road.jpg", "frame_youtube.jpg",
        "yt_annotated_sample.jpg", "sih_check_*.jpg", "sih_frame_*.jpg"
    ]
    for pat in root_patterns:
        for f in glob.glob(pat):
            safe_remove(f)

    # 3. Duplicate and intermediate video download files
    safe_remove("real_road_demo.mp4")
    safe_remove("test_bus_lane_change.mp4")
    safe_remove(os.path.join("server", "static", "real_road_demo.mp4"))
    safe_remove(os.path.join("server", "static", "youtube_demo.f605.mp4"))
    safe_remove(os.path.join("server", "static", "youtube_demo.f140.m4a"))

    # 4. Old zip file in root (we will regenerate freshly)
    safe_remove("BEL_UrbanSense_Project.zip")

    # 5. Clean up the 75,000+ cached snapshot image dumps in server/static/uploads
    # Keep the most recent 50 images for UI gallery, delete the remaining 75,000+
    uploads_dir = os.path.join("server", "static", "uploads")
    if os.path.exists(uploads_dir):
        all_uploads = []
        for entry in os.scandir(uploads_dir):
            if entry.is_file():
                all_uploads.append((entry.path, entry.stat().st_mtime, entry.stat().st_size))
        
        # Sort by mtime descending (newest first)
        all_uploads.sort(key=lambda x: x[1], reverse=True)
        to_delete = all_uploads[50:]  # Keep top 50 newest, delete the rest
        
        print(f" [*] Cleaning {len(to_delete)} accumulated snapshot frames in uploads/...")
        for p, _, sz in to_delete:
            try:
                os.remove(p)
                freed_bytes += sz
                deleted_count += 1
            except Exception:
                pass

    print("=" * 65)
    print(f"[+] CLEANUP COMPLETED SUCCESSFULLY!")
    print(f"[+] Total files deleted: {deleted_count:,}")
    print(f"[+] Total disk space reclaimed: {freed_bytes / (1024 * 1024):.1f} MB ({freed_bytes / (1024 * 1024 * 1024):.2f} GB)")
    print("=" * 65)

if __name__ == "__main__":
    run_cleanup()
