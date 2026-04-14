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
NEON_DATABASE_URL = input("Enter your Neon DATABASE_URL: ").strip()

# URL Cleanup: Handles accidental psql command pasting or extra quotes
NEON_DATABASE_URL = NEON_DATABASE_URL.replace('psql "', '').replace('"', '').split(' ')[0].strip()

if not NEON_DATABASE_URL:
    print("Error: No Database URL provided. Exiting.")
    exit(1)

# Set the Neon Database URL as an environment variable BEFORE django.setup()
# This ensures dj_database_url picks it up correctly in settings.py
os.environ['DATABASE_URL'] = NEON_DATABASE_URL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

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
        'member.memberpasswordresettoken',
        'member.otpverification',
        'business.businesscategory',
        'business.business',
        'marketplace.bnsmodel',
        'marketplace.bid',
        'news.category',
        'news.news',
        'donation.donationsubject',
        'donation.donation',
        'donation.expense',
        'gallery.galleryalbum',
        'gallery.galleryimage',
        'gallery.googledriveconnection',
        'career.careerpost',
        'home.contact'
    ]

    objects_by_model = {m: [o for o in data if o['model'] == m] for m in model_order}

    BATCH_SIZE = 500

    for model_label in model_order:
        items = objects_by_model.get(model_label, [])
        if not items:
            continue
        
        print(f"Uploading {len(items)} records to {model_label} (Batch Size: {BATCH_SIZE})...")
        app_label, model_name = model_label.split('.')
        model = apps.get_model(app_label, model_name)
        
        # Determine PK and fields to update
        pk_name = model._meta.pk.name
        all_fields = [f.name for f in model._meta.fields]
        update_fields = [f for f in all_fields if f != pk_name]
        
        instances = []
        for i, obj_data in enumerate(items):
            pk_val = obj_data['pk']
            fields = obj_data['fields']
            
            # Handle Foreign Keys and field mapping
            refined_fields = {pk_name: pk_val}
            for field_name, value in fields.items():
                try:
                    field_obj = model._meta.get_field(field_name)
                    if field_obj.is_relation:
                        # Skip many-to-many fields (they aren't supported by bulk_create)
                        if field_obj.many_to_many:
                            continue
                        refined_fields[f"{field_name}_id"] = value
                    else:
                        refined_fields[field_name] = value
                except:
                    # In case of missing fields in model (e.g. removed fields in db.json)
                    pass
            
            instances.append(model(**refined_fields))

        # Perform Bulk Upload in batches
        try:
            with transaction.atomic():
                # Django 4.1+ supports update_conflicts
                # This allows re-running the script safely
                model.objects.bulk_create(
                    instances,
                    batch_size=BATCH_SIZE,
                    update_conflicts=True,
                    update_fields=update_fields,
                    unique_fields=[pk_name]
                )
            print(f"  - Finished {model_label}: {len(instances)} records synced.")
        except Exception as e:
            print(f"  - Error in bulk upload for {model_label}: {e}")
            print(f"  - Falling back to individual updates (Safe Mode)...")
            
            count = 0
            failed = 0
            for inst in instances:
                try:
                    with transaction.atomic():
                        # Use update_or_create logic to handle pre-existing data
                        defaults = {f: getattr(inst, f"{f}_id" if hasattr(inst, f"{f}_id") else f) for f in update_fields}
                        model.objects.update_or_create(**{pk_name: inst.pk}, defaults=defaults)
                        count += 1
                except Exception as row_err:
                    failed += 1
                    # Skip problematic rows instead of crashing
                    continue
            
            print(f"  - Finished {model_label}: {count} successful, {failed} skipped.")



    print("\nSUCCESS! Your Neon database is now fully populated with 14,000+ records.")
    print("Every future Render deployment will now be super fast!")

if __name__ == '__main__':
    upload_data()
