import os
import zipfile

def create_zip():
    zip_name = "BEL_UrbanSense_Project.zip"
    exclude_dirs = {'.git', 'venv', '__pycache__', 'node_modules', '.agents', '.system_generated'}
    
    print("=" * 65)
    print(" [*] Packaging BEL UrbanSense for sharing...")
    print(" [*] Excluding heavy cache dumps (5GB+ uploads, venv)...")
    print("=" * 65)
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            if 'uploads' in root.replace('\\', '/'):
                continue
            for file in files:
                if file.endswith('.zip') or file.endswith('.pyc') or file.endswith('.log'):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, '.')
                z.write(full_path, rel_path)
        
        # Ensure uploads folder exists in zip
        z.writestr('server/static/uploads/.gitkeep', '')
        
    size_mb = os.path.getsize(zip_name) / (1024 * 1024)
    print(f"\n[+] SUCCESS! Created '{zip_name}' ({size_mb:.1f} MB)")
    print(f"[+] File location: {os.path.abspath(zip_name)}")
    print("\nHow your friends can run it:")
    print(" 1. Send them this zip file (via Google Drive, WeTransfer, WhatsApp Web, or Pendrive).")
    print(" 2. They extract the zip on their laptop.")
    print(" 3. They double-click 'SETUP_NEW_LAPTOP.bat'. Everything runs automatically!")
    print("=" * 65)

if __name__ == "__main__":
    create_zip()
