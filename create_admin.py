import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.apps import apps
from django.db import transaction

# 1. Create Superuser
username = os.environ.get('ADMIN_USERNAME', 'admin')
password = os.environ.get('ADMIN_PASSWORD', 'Password123')
email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

User = get_user_model()

if not User.objects.filter(username=username).exists():
    try:
        User.objects.create_superuser(username, email, password)
        print(f"Superuser '{username}' created successfully!")
    except Exception as e:
        print(f"Error creating superuser: {e}")
else:
    print(f"Superuser '{username}' already exists.")

# 2. Load Minimal Data (Countries, Cities, Categories)
def load_minimal_data():
    file_path = 'db.json'
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found. Skipping data load.")
        return

    print(f"Reading data from {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    print(f"Loaded {len(data)} objects from JSON.")

    # Order ensures parent records exist before children
    model_order = [
        'auth.user',
        'member.country',
        'member.member',
        'member.memberdetail',
        'business.businesscategory',
        'news.category',
        'donation.donationsubject'
    ]

    objects_by_model = {}
    for obj in data:
        model_name = obj['model']
        if model_name not in objects_by_model:
            objects_by_model[model_name] = []
        objects_by_model[model_name].append(obj)

    for model_label in model_order:
        if model_label not in objects_by_model:
            continue
        
        print(f"Processing model: {model_label}...")
        app_label, model_name = model_label.split('.')
        try:
            model = apps.get_model(app_label, model_name)
        except Exception as e:
            print(f"  - Error: Model {model_label} not found: {e}")
            continue
        
        count = 0
        with transaction.atomic():
            for obj_data in objects_by_model[model_label]:
                pk = obj_data['pk']
                fields = obj_data['fields']
                
                # Handle Foreign Keys more robustly
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
                    obj, created = model.objects.update_or_create(
                        pk=pk,
                        defaults=refined_fields
                    )
                    count += 1
                except Exception as e:
                    # Silently skip errors for individual records but log the count
                    pass

        print(f"  - Successfully imported/updated {count} {model_label} records.")

if __name__ == '__main__':
    # load_minimal_data() # DEPRECATED: Use upload_to_neon.py locally for faster deployment
    print("Initialization complete.")
