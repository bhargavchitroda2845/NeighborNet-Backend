import os
import django
import sys

# Setup Django
sys.path.append(r'D:\NeighborNet\hello')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from gallery.models import GoogleDriveConnection, Member, GalleryAlbum, GalleryImage
from gallery.google_drive_utils import get_drive_service

def audit_member_36():
    m = Member.objects.get(member_no=36)
    conn = GoogleDriveConnection.objects.get(member=m)
    service = get_drive_service(conn)
    
    print(f"Current Root: {conn.folder_id}")
    
    # List all files recursively in that root
    def list_files(parent_id, indent=""):
        query = f"'{parent_id}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])
        for f in files:
            print(f"{indent}File: {f['name']} (ID: {f['id']}) Type: {f['mimeType']}")
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                list_files(f['id'], indent + "  ")

    list_files(conn.folder_id)

if __name__ == "__main__":
    audit_member_36()
