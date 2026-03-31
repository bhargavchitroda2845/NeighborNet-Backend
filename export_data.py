import os
import django
import json
from django.core import serializers

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

# List of specific models to export (AppLabel:ModelName)
# Based on your request: only countries, cities, and categories.
# Excludes members, marketplace items, news items, etc.
target_models = {
    'member': ['Country', 'State', 'City'],
    'business': ['BusinessCategory'],
    'news': ['Category'],
    'donation': ['DonationSubject'],
}

all_data = []

from django.apps import apps as django_apps

for app_label, model_names in target_models.items():
    print(f"Exporting models from {app_label}...")
    try:
        app_config = django_apps.get_app_config(app_label)
        for model_name in model_names:
            print(f"  - Model: {model_name}")
            model = app_config.get_model(model_name)
            objects = model.objects.all()
            data = serializers.serialize('json', objects)
            all_data.extend(json.loads(data))
            
    except Exception as e:
        print(f"Error exporting {app_label}.{model_name}: {e}")

# Save to file with UTF-8 encoding
with open('db.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False)

print("Export complete: db.json created with only Countries, Cities, and Categories.")
