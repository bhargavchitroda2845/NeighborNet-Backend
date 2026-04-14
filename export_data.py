import os
import django
import json
from django.core import serializers

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

# Full list of models to export for the Neon database 
# (Country, State, City, Categories, Members, and Users)
target_models = {
    'auth': ['User'],
    'member': ['Country', 'State', 'City', 'Member', 'MemberDetail', 'MemberPasswordResetToken', 'OTPVerification'],
    'business': ['BusinessCategory', 'Business'],
    'news': ['Category', 'News'],
    'donation': ['DonationSubject', 'Donation', 'Expense'],
    'marketplace': ['BnsModel', 'Bid'],
    'gallery': ['GalleryAlbum', 'GalleryImage', 'GoogleDriveConnection'],
    'career': ['CareerPost'],
    'home': ['Contact'],
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

print("Export complete: FULL db.json created for direct Neon upload.")
