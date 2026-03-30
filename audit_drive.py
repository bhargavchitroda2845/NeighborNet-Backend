import os
import django
import sys
import json

# Setup Django
sys.path.append(r'D:\NeighborNet\hello')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from gallery.models import GoogleDriveConnection, Member
from gallery.google_drive_utils import get_drive_service

def audit_drive():
    for connection in GoogleDriveConnection.objects.all():
        print(f"\n--- AUDIT FOR {connection.member.username} ---")
        print(f"Root Folder ID: {connection.folder_id}")
        
        service = get_drive_service(connection)
        if not service:
            print("FAILED to get drive service")
            continue
            
        try:
            # Check root
            root = service.files().get(fileId=connection.folder_id, fields='id, name, trashed').execute()
            print(f"Root Folder '{root.get('name')}' exists. Trashed: {root.get('trashed')}")
            
            # List subfolders
            query = f"'{connection.folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            print(f"Found {len(folders)} sub-folders (albums)")
            
            for f in folders:
                print(f"  Album Folder: {f['name']} (ID: {f['id']})")
                # List files inside
                q_files = f"'{f['id']}' in parents and trashed = false"
                res_files = service.files().list(q=q_files, fields="files(id, name, mimeType)").execute()
                files = res_files.get('files', [])
                print(f"    - {len(files)} files found")
                for img in files[:3]:
                    print(f"      File: {img['name']} ({img['mimeType']}) ID: {img['id']}")
                    try:
                        content = service.files().get_media(fileId=img['id']).execute()
                        print(f"        DOWNLOAD TEST: {len(content)} bytes received, Type: {type(content)}")
                        if len(content) > 0:
                            print(f"        FIRST 10 BYTES: {content[:10].hex()}")
                    except Exception as de:
                        print(f"        DOWNLOAD FAILED: {de}")
                    
        except Exception as e:
            print(f"ERROR auditing drive for {connection.member.username}: {e}")

if __name__ == "__main__":
    audit_drive()
