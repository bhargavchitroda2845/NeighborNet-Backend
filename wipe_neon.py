import os
import django
import dj_database_url
from django.conf import settings

# 1. SETUP
print("WARNING: This script will WIPE all data (except Users) from your Neon database.")
NEON_URL = input("Paste your Neon DATABASE_URL: ").strip()

# URL Cleanup
NEON_URL = NEON_URL.replace('psql "', '').replace('"', '').split(' ')[0].strip()

if not NEON_URL:
    print("Error: No URL provided.")
    exit()

os.environ['DATABASE_URL'] = NEON_URL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from django.db import connection, transaction

# THE REVERSE ORDER (Children first)
tables_to_wipe = [
    'home_contact',
    'career_careerpost',
    'gallery_googledriveconnection',
    'gallery_galleryimage',
    'gallery_galleryalbum',
    'donation_expense',
    'donation_donation',
    'donation_donationsubject',
    'news_news',
    'news_category',
    'marketplace_bid',
    'bns_model',  # Marketplace table name
    'business_business',
    'business_business_businesscategory',
    'business_businesscategory',
    'member_otpverification',
    'member_memberpasswordresettoken',
    'member_memberdetail',
    'member_member',
    'member_city',
    'member_state',
    'member_country',
    # We SKIP 'auth_user' to keep your admin account
]

print("\nStarting Wipe Operation...")
try:
    with connection.cursor() as cursor:
        # Disable foreign key checks for the wipe (PostgreSQL style)
        cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
        
        for table in tables_to_wipe:
            try:
                print(f"  - Wiping {table}...")
                # CASCADE handles any remaining dependencies
                cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
            except Exception as e:
                print(f"    (Skipped {table}: {e})")
                
    print("\nSUCCESS! Neon database is now clean (except for Users).")
except Exception as e:
    print(f"\nError during wipe: {e}")
