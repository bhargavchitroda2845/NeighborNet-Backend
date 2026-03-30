import os
import django
import sys

# Setup Django
sys.path.append(r'D:\NeighborNet\hello')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from gallery.models import GoogleDriveConnection, Member, GalleryAlbum, GalleryImage

def audit_all():
    print("=== MEMBER DATABASE AUDIT ===")
    for m in Member.objects.all().order_by('member_no'):
        conn = GoogleDriveConnection.objects.filter(member=m).first()
        status = "CONNECTED" if (conn and conn.credentials_data) else "NOT CONNECTED"
        folder = conn.folder_id if conn else "N/A"
        print(f"[{m.member_no}] Username: {m.username}, Display: {m.first_name} {m.surname}")
        print(f"    Drive Status: {status}, Root: {folder}")
        
    print("\n=== FAILING IMAGE OWNERSHIP ===")
    failing_ids = [
        '1e3EzYj19Fei4X72gpLejOeFdJ7Uv0bYL',
        '1wDYY3z72aJG8_sN4oNaKf2A9n307g_vj',
        '1GOpoA3m3dJywnHCYCFThBe3Eb5wIJDB6',
        '1DyYn4nctlBdEHPY8CN5zw7JbLg9UuGgS' # Working one
    ]
    
    for fid in failing_ids:
        img = GalleryImage.objects.filter(google_drive_file_id=fid).select_related('album__member').first()
        if img:
            owner = img.album.member
            print(f"File ID: {fid}")
            print(f"    Album: {img.album.title} (ID: {img.album.id})")
            print(f"    Owner: {owner.username} (ID: {owner.member_no})")
        else:
            # Check albums
            alb = GalleryAlbum.objects.filter(google_drive_file_id=fid).select_related('member').first()
            if alb:
                print(f"File ID: {fid} (Album Cover)")
                print(f"    Album: {alb.title} (ID: {alb.id})")
                print(f"    Owner: {alb.member.username} (ID: {alb.member.member_no})")
            else:
                print(f"File ID: {fid} - NOT FOUND IN DATABASE")

if __name__ == "__main__":
    audit_all()
