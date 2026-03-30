import os
import django
import sys

# Setup Django
sys.path.append(r'D:\NeighborNet\hello')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from gallery.models import GoogleDriveConnection, Member, GalleryImage
from gallery.google_drive_utils import get_drive_service

def final_audit():
    failing_ids = [
        '1e3EzYj19Fei4X72gpLejOeFdJ7Uv0bYL',
        '1wDYY3z72aJG8_sN4oNaKf2A9n307g_vj',
        '1GOpoA3m3dJywnHCYCFThBe3Eb5wIJDB6'
    ]
    
    connections = GoogleDriveConnection.objects.all()
    print(f"Total Connections found: {connections.count()}")
    
    for conn in connections:
        m = conn.member
        print(f"\nConnection for Member: {m.username} (ID: {m.member_no})")
        print(f"Root Folder: {conn.folder_id}")
        
        service = get_drive_service(conn)
        if not service:
            print("  FAILED to get service.")
            continue
            
        for fid in failing_ids:
            try:
                meta = service.files().get(fileId=fid, fields='id, name').execute()
                print(f"  [FOUND] {fid} -> '{meta.get('name')}'")
            except Exception as e:
                print(f"  [MISSING] {fid} -> Error: {e}")

if __name__ == "__main__":
    final_audit()
