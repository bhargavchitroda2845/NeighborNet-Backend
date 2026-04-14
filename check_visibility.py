import os
import django
import dj_database_url
from django.conf import settings

# 1. SETUP
NEON_URL = input("Paste your Neon DATABASE_URL: ").strip()
NEON_URL = NEON_URL.replace('psql "', '').replace('"', '').split(' ')[0].strip()

os.environ['DATABASE_URL'] = NEON_URL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from django.db.models import Count
from marketplace.models import BnsModel
from news.models import News

# 2. CHECK STATUS
print("\n--- CONTENT VISIBILITY CHECK ---")

bns_counts = BnsModel.objects.values('status').annotate(count=models.Count('id'))
print("\nMarketplace Statuses:")
for b in bns_counts:
    print(f"  - {b['status']}: {b['count']}")

news_counts = News.objects.values('status').annotate(count=models.Count('id'))
print("\nNews Statuses:")
for n in news_counts:
    print(f"  - {n['status']}: {n['count']}")

# 3. SAMPLE
print("\nSample Marketplace Item:")
first_item = BnsModel.objects.first()
if first_item:
    print(f"  - Title: {first_item.title}")
    print(f"  - Status: {first_item.status}")
    print(f"  - Published At: {first_item.published_at}")
else:
    print("  - No items found!")

print("--------------------------------\n")
