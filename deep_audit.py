import os
import django
import sys
import json

# Setup Django
sys.path.append(r'D:\NeighborNet\hello')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from gallery.models import GoogleDriveConnection, Member, GalleryImage
from gallery.google_drive_utils import get_drive_service

def deep_audit():
    # IDs from the user's logs
    failing_ids = [
        '1e3EzYj19Fei4X72gpLejOeFdJ7Uv0bYL',
        '1wDYY3z72aJG8_sN4oNaKf2A9n307g_vj',
        '1GOpoA3m3dJywnHCYCFThBe3Eb5wIJDB6'
    ]
    
    # Use the connection for bhargavchitroda2 (if possible) or just find any connection
    conn = GoogleDriveConnection.objects.first()
    if not conn:
        print("No connections found.")
        return
        
    service = get_drive_service(conn)
    if not service:
        print("Failed to get service.")
        return
        
    for file_id in failing_ids:
        print(f"\n--- DEEP METADATA FOR {file_id} ---")
        try:
            meta = service.files().get(fileId=file_id, fields='*').execute()
            print(json.dumps(meta, indent=2))
        except Exception as e:
            print(f"FAILED to get metadata: {e}")

if __name__ == "__main__":
    deep_audit()
