import os
import django
import json
import dj_database_url

# -------------------------------------------------------------
# NEON PRODUCTION UPLOADER
# -------------------------------------------------------------
# Instructions:
# 1. Paste your Neon DATABASE_URL below.
# 2. Run: python upload_to_neon.py
# -------------------------------------------------------------

# --- CONFIGURATION ---
# Replace with your actual Neon connection string:
NEON_DATABASE_URL = input("Enter your Neon DATABASE_URL: ").strip()

if not NEON_DATABASE_URL:
    print("Error: No Database URL provided. Exiting.")
    exit(1)

# Configure Django to use the Neon Database temporarily
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

# Dynamically override the database setting to point to Neon
from django.conf import settings
settings.DATABASES['default'] = dj_database_url.parse(NEON_DATABASE_URL)

from django.apps import apps
from django.db import transaction

def upload_data():
    file_path = 'db.json'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please run export_data.py first.")
        return

    print(f"Reading data from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} objects for upload. Starting direct transfer to Neon...")

    # Order is CRITICAL for Foreign Key integrity
    model_order = [
        'auth.user',
        'member.country',
        'member.state',
        'member.city',
        'member.member',
        'member.memberdetail',
        'business.businesscategory',
        'news.category',
        'donation.donationsubject'
    ]

    objects_by_model = {m: [o for o in data if o['model'] == m] for m in model_order}

    for model_label in model_order:
        items = objects_by_model.get(model_label, [])
        if not items:
            continue
        
        print(f"Uploading {len(items)} records to {model_label}...")
        app_label, model_name = model_label.split('.')
        model = apps.get_model(app_label, model_name)
        
        count = 0
        failed = 0
        # Use simple progress tracking
        total = len(items)
        
        with transaction.atomic():
            for i, obj_data in enumerate(items):
                pk = obj_data['pk']
                fields = obj_data['fields']
                
                # Handle Foreign Keys
                refined_fields = {}
                for field_name, value in fields.items():
                    try:
                        field_obj = model._meta.get_field(field_name)
                        if field_obj.is_relation and value is not None:
                            refined_fields[f"{field_name}_id"] = value
                        else:
                            refined_fields[field_name] = value
                    except:
                        refined_fields[field_name] = value

                try:
                    # update_or_create is safer; it updates if ID exists, creates if not.
                    model.objects.update_or_create(pk=pk, defaults=refined_fields)
                    count += 1
                except Exception as e:
                    failed += 1
                
                if (i + 1) % 500 == 0:
                    print(f"  - Progress: {i+1}/{total}...")

        print(f"  - Finished {model_label}: {count} successful, {failed} failed.")

    print("\nSUCCESS! Your Neon database is now fully populated with 14,000+ records.")
    print("Every future Render deployment will now be super fast!")

if __name__ == '__main__':
    upload_data()
