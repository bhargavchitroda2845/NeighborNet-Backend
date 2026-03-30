#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from business.models import BusinessCategory

CATEGORIES = [
    {"name": "Home & Building Work", "icon": "🏠"},
    {"name": "Stitching, Tailoring & Hand Work", "icon": "👗"},
    {"name": "Shops & Daily Needs", "icon": "🛒"},
    {"name": "Food & Tiffin Services", "icon": "🍽️"},
    {"name": "Vehicle & Transport Services", "icon": "🚗"},
    {"name": "Computer, Mobile & Tech Services", "icon": "💻"},
    {"name": "Health, Care & Wellness", "icon": "🧑‍⚕️"},
    {"name": "Education & Training", "icon": "📚"},
    {"name": "Events, Media & Creative Work", "icon": "🎉"},
    {"name": "Personal & Local Services", "icon": "🧹"},
]

print("Seeding business categories...")
print("-" * 40)

created = 0
updated = 0

for cat in CATEGORIES:
    category, is_new = BusinessCategory.objects.update_or_create(
        name=cat["name"],
        defaults={"icon": cat["icon"], "is_active": True}
    )
    if is_new:
        created += 1
        print(f"Created: {category.name} {category.icon}")
    else:
        updated += 1
        print(f"Updated: {category.name} {category.icon}")

print("-" * 40)
print(f"Done! Created: {created}, Updated: {updated}")
print(f"Total categories in database: {BusinessCategory.objects.count()}")

