import os
import django
import json

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from django.apps import apps
from django.db import transaction

def run_import():
    file_path = 'db.json'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    print(f"Reading data from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} objects from JSON.")

    # Sort models to ensure parent records (Country, State) are created before children (City)
    # Order: Country -> State -> City -> Categories
    model_order = [
        'member.country',
        'member.state',
        'member.city',
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
        model = apps.get_model(app_label, model_name)
        
        count = 0
        with transaction.atomic():
            for obj_data in objects_by_model[model_label]:
                pk = obj_data['pk']
                fields = obj_data['fields']
                
                # Handle Foreign Keys
                # We need to convert ID fields to actual model instances if they are many-to-one
                refined_fields = {}
                for field_name, value in fields.items():
                    field_obj = model._meta.get_field(field_name)
                    if field_obj.is_relation and value is not None:
                        # It's a foreign key, we can just use the ID because Django handles it via field_id
                        refined_fields[f"{field_name}_id"] = value
                    else:
                        refined_fields[field_name] = value

                try:
                    obj, created = model.objects.update_or_create(
                        pk=pk,
                        defaults=refined_fields
                    )
                    count += 1
                except Exception as e:
                    print(f"  - Error importing {model_label} (PK {pk}): {e}")

        print(f"  - Successfully imported/updated {count} {model_label} records.")

    print("Data import complete!")

if __name__ == '__main__':
    run_import()
