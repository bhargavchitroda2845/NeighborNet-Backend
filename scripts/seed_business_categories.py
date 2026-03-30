"""
Script to seed business categories into the database.
Run with: python manage.py runscript seed_business_categories
"""

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


def run():
    created_count = 0
    updated_count = 0
    
    for cat_data in CATEGORIES:
        category, created = BusinessCategory.objects.update_or_create(
            name=cat_data["name"],
            defaults={
                "icon": cat_data["icon"],
                "is_active": True,
            }
        )
        if created:
            created_count += 1
            print(f"Created: {category.name} ({category.icon})")
        else:
            updated_count += 1
            print(f"Updated: {category.name} ({category.icon})")
    
    print(f"\n✅ Done! Created: {created_count}, Updated: {updated_count}")
    print(f"Total categories in database: {BusinessCategory.objects.count()}")

