import os
import django
import sys
import json

# Setup Django
sys.path.append(r'D:\NeighborNet\hello')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from gallery.models import GoogleDriveConnection, Member, GalleryAlbum, GalleryImage
from gallery.google_drive_utils import get_drive_service

def audit_members():
    print("--- MEMBER AUDIT ---")
    for member in Member.objects.all():
        conn = GoogleDriveConnection.objects.filter(member=member).first()
        album_count = GalleryAlbum.objects.filter(member=member).count()
        print(f"Member: {member.username} (ID: {member.member_no})")
        print(f"  Drive Connected: {bool(conn and conn.credentials_data)}")
        print(f"  Albums: {album_count}")
        
        if conn and conn.credentials_data:
            service = get_drive_service(conn)
            if service:
                # Test a random file access if any
                img = GalleryImage.objects.filter(album__member=member, google_drive_file_id__isnull=False).first()
                if img:
                    print(f"  Testing access to file {img.google_drive_file_id}...")
                    try:
                        content = service.files().get_media(fileId=img.google_drive_file_id).execute()
                        print(f"    SUCCESS: Received {len(content)} bytes")
                    except Exception as e:
                        print(f"    FAILED: {e}")
                else:
                    print("  No images to test for this member.")
            else:
                print("  FAILED to get drive service")

if __name__ == "__main__":
    audit_members()
