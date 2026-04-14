import os
import django
import dj_database_url
from django.conf import settings

# 1. SETUP
print("Note: This script will verify the REAL counts on your Neon server.")
NEON_URL = input("Paste your Neon DATABASE_URL: ").strip()

if not NEON_URL:
    print("Error: No URL provided.")
    exit()

# Set environment variable BEFORE django.setup()
os.environ['DATABASE_URL'] = NEON_URL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

# 2. MODELS
from member.models import Member
from marketplace.models import BnsModel
from news.models import News

# 3. CHECK
try:
    print("\n--- NEON DATABASE STATUS ---")
    print(f"Members: {Member.objects.count()}")
    print(f"Marketplace Items (BNS): {BnsModel.objects.count()}")
    print(f"News Items: {News.objects.count()}")
    print("----------------------------\n")
except Exception as e:
    print(f"Error checking database: {e}")
