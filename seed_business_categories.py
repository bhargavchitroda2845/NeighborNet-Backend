#!/usr/bin/env python
"""
Script to seed Business Categories into the database.
Run with: python manage.py shell < seed_business_categories.py
"""
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

def seed_categories():
    print("Seeding Business Categories...")
    created_count = 0
    skipped_count = 0
    
    for cat_data in CATEGORIES:
        # Check if category already exists
        if BusinessCategory.objects.filter(name=cat_data["name"]).exists():
            print(f"  - Skipped: {cat_data['name']} (already exists)")
            skipped_count += 1
            continue
        
        category = BusinessCategory.objects.create(
            name=cat_data["name"],
            icon=cat_data["icon"],
            is_active=True
        )
        print(f"  - Created: {category.name} ({category.icon})")
        created_count += 1
    
    print(f"\nDone! Created {created_count} categories, skipped {skipped_count} existing categories.")
    print(f"\nTotal categories in database: {BusinessCategory.objects.count()}")

if __name__ == "__main__":
    seed_categories()

