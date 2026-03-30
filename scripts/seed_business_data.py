"""
Script to seed business data into the database.
Run with: python manage.py runscript seed_business_data
"""

from business.models import Business, BusinessCategory
from django.utils import timezone
import os

# Business data matching the JSON file
BUSINESSES = [
    {
        "name": "Shree Civil Works",
        "category": "Home & Building Work",
        "service": "Civil Work",
        "location": "Ahmedabad",
        "area": "CG Road",
        "phone": "9876543210",
        "details": "House construction, RCC work, renovation, repair work",
        "address": "123 Main Road, Ahmedabad",
        "working_hours": "9 AM - 6 PM",
    },
    {
        "name": "Raj Electrician",
        "category": "Home & Building Work",
        "service": "Electrician",
        "location": "Surat",
        "area": "Ring Road",
        "phone": "9876501234",
        "details": "House wiring, switch repair, inverter & LED fitting",
        "address": "45 commercial complex, Surat",
        "working_hours": "8 AM - 8 PM",
    },
    {
        "name": "Perfect Plumbing",
        "category": "Home & Building Work",
        "service": "Plumber",
        "location": "Vadodara",
        "area": "Alkapuri",
        "phone": "9898989898",
        "details": "Leakage fixing, bathroom fittings, water motor repair",
        "address": "78 Pipeline Road, Vadodara",
        "working_hours": "7 AM - 7 PM",
    },
    {
        "name": "Meera Tailors",
        "category": "Stitching, Tailoring & Hand Work",
        "service": "Ladies Tailor",
        "location": "Ahmedabad",
        "area": "Prahlad Nagar",
        "phone": "9988776655",
        "details": "Blouse stitching, dress alteration, custom fitting",
        "address": "Fashion Street, Ahmedabad",
        "working_hours": "10 AM - 7 PM",
    },
    {
        "name": "Royal Boutique",
        "category": "Stitching, Tailoring & Hand Work",
        "service": "Boutique",
        "location": "Surat",
        "area": "Varachha",
        "phone": "9123456789",
        "details": "Designer dresses, embroidery, wedding wear",
        "address": "Wedding Plaza, Surat",
        "working_hours": "10 AM - 8 PM",
    },
    {
        "name": "Patel Kirana Store",
        "category": "Shops & Daily Needs",
        "service": "Grocery Shop",
        "location": "Rajkot",
        "area": "Kalavad Road",
        "phone": "9000011111",
        "details": "All daily grocery items, home delivery available",
        "address": "Shop No. 12, Rajkot",
        "working_hours": "8 AM - 9 PM",
    },
    {
        "name": "Shiv Medical",
        "category": "Shops & Daily Needs",
        "service": "Medical Store",
        "location": "Ahmedabad",
        "area": "SG Highway",
        "phone": "9888888888",
        "details": "All medicines, surgical items, doctor prescriptions",
        "address": "Health Center, Ahmedabad",
        "working_hours": "24 Hours",
    },
    {
        "name": "Maa Tiffin Service",
        "category": "Food & Tiffin Services",
        "service": "Home Tiffin",
        "location": "Ahmedabad",
        "area": "Bopal",
        "phone": "9090909090",
        "details": "Pure veg home food, monthly lunch & dinner plans",
        "address": "Home Kitchen, Bopal",
        "working_hours": "7 AM - 10 PM",
    },
    {
        "name": "Shree Catering",
        "category": "Food & Tiffin Services",
        "service": "Catering",
        "location": "Surat",
        "area": "Adajan",
        "phone": "9345678901",
        "details": "Marriage, party & function catering services",
        "address": "Catering Unit, Surat",
        "working_hours": "By Appointment",
    },
    {
        "name": "City Cab Service",
        "category": "Vehicle & Transport Services",
        "service": "Cab Service",
        "location": "Ahmedabad",
        "area": "Airport Road",
        "phone": "9012345678",
        "details": "Local & outstation cab service, airport pickup",
        "address": "Cab Stand, Ahmedabad",
        "working_hours": "24 Hours",
    },
    {
        "name": "Fast Bike Repair",
        "category": "Vehicle & Transport Services",
        "service": "Bike Mechanic",
        "location": "Surat",
        "area": "Katargam",
        "phone": "9555555555",
        "details": "Bike servicing, puncture, engine repair",
        "address": "Bike Garage, Surat",
        "working_hours": "9 AM - 7 PM",
    },
    {
        "name": "Mobile Care",
        "category": "Computer, Mobile & Tech Services",
        "service": "Mobile Repair",
        "location": "Ahmedabad",
        "area": "Maninagar",
        "phone": "9666666666",
        "details": "Screen replacement, battery change, software issues",
        "address": "Tech Plaza, Ahmedabad",
        "working_hours": "10 AM - 8 PM",
    },
    {
        "name": "WebTech Solutions",
        "category": "Computer, Mobile & Tech Services",
        "service": "Website Development",
        "location": "Remote",
        "area": "Online",
        "phone": "9777777777",
        "details": "Website, software & mobile app development",
        "address": "Remote Service",
        "working_hours": "9 AM - 6 PM",
    },
    {
        "name": "Shree Clinic",
        "category": "Health, Care & Wellness",
        "service": "Clinic",
        "location": "Vadodara",
        "area": "Sayajigunj",
        "phone": "9444444444",
        "details": "General physician, health checkups",
        "address": "Medical Building, Vadodara",
        "working_hours": "9 AM - 1 PM, 5 PM - 8 PM",
    },
    {
        "name": "Bright Tuition",
        "category": "Education & Training",
        "service": "School Tuition",
        "location": "Ahmedabad",
        "area": "Thaltej",
        "phone": "9333333333",
        "details": "Classes 1–10 tuition, maths & science",
        "address": "Education Hub, Ahmedabad",
        "working_hours": "4 PM - 8 PM",
    },
    {
        "name": "Dream Events",
        "category": "Events, Media & Creative Work",
        "service": "Event Decoration",
        "location": "Surat",
        "area": "Piplod",
        "phone": "9222222222",
        "details": "Wedding, birthday & corporate event decoration",
        "address": "Event Arena, Surat",
        "working_hours": "By Appointment",
    },
    {
        "name": "Quick Pest Control",
        "category": "Personal & Local Services",
        "service": "Pest Control",
        "location": "Ahmedabad",
        "area": "Panjrapole",
        "phone": "9111111111",
        "details": "Termite, cockroach & mosquito control",
        "address": "Service Center, Ahmedabad",
        "working_hours": "8 AM - 6 PM",
    },
]


def run():
    created_count = 0
    updated_count = 0
    
    # First, create categories if they don't exist
    categories_map = {}
    for cat_data in [
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
    ]:
        category, created = BusinessCategory.objects.update_or_create(
            name=cat_data["name"],
            defaults={"icon": cat_data["icon"], "is_active": True}
        )
        categories_map[cat_data["name"]] = category
        if created:
            print(f"Created category: {category.name}")
    
    print(f"\nTotal categories: {len(categories_map)}")
    
    # Now create businesses
    for biz_data in BUSINESSES:
        category_name = biz_data.pop("category")
        category = categories_map.get(category_name)
        
        # Check if business already exists
        existing_business = Business.objects.filter(name=biz_data["name"]).first()
        
        if existing_business:
            # Update existing business
            for key, value in biz_data.items():
                setattr(existing_business, key, value)
            existing_business.category = category
            existing_business.status = "published"
            existing_business.published_at = timezone.now()
            existing_business.save()
            updated_count += 1
            print(f"Updated: {existing_business.name}")
        else:
            # Create new business
            business = Business(
                name=biz_data["name"],
                category=category,
                service=biz_data["service"],
                location=biz_data["location"],
                area=biz_data.get("area", ""),
                phone=biz_data["phone"],
                details=biz_data.get("details", ""),
                address=biz_data.get("address", ""),
                working_hours=biz_data.get("working_hours", ""),
                status="published",
                published_at=timezone.now(),
            )
            business.save()
            created_count += 1
            print(f"Created: {business.name}")
    
    print(f"\n✅ Done! Created: {created_count}, Updated: {updated_count}")
    print(f"Total businesses in database: {Business.objects.count()}")

