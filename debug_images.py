import os
import django
import sys

# Setup Django
sys.path.append(r'D:\NeighborNet\hello')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from gallery.models import GalleryAlbum, GalleryImage

print("--- RECENT ALBUMS ---")
for album in GalleryAlbum.objects.all().order_by('-created_at')[:5]:
    print(f"ID: {album.id}, Title: {album.title}, Drive ID: {album.google_drive_file_id}, Status: {album.status}")

print("\n--- RECENT IMAGES ---")
for img in GalleryImage.objects.all().order_by('-created_at')[:10]:
    print(f"ID: {img.id}, Album: {img.album.title}, Drive ID: {img.google_drive_file_id}, Status: {img.status}")
