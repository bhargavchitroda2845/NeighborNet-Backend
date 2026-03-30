from datetime import timedelta
import os
import random
import django
from django.utils import timezone
from django.utils.text import slugify

# Ensure Django is set up when running as a standalone script
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hello.settings")
django.setup()

from marketplace.models import BnsModel  # noqa: E402
from member.models import Member  # noqa: E402


# Config
RECORD_COUNT = 100
HOURS_STEP = 2


member_instance = Member.objects.first()
if not member_instance:
    raise SystemExit("No Member found. Create at least one Member, then rerun.")


titles = [
    "2BHK Flat for Rent",
    "Used Bike for Sale",
    "Shop Space Needed",
    "Laptop for Sale",
    "Looking for 1RK Rental",
    "Car for Immediate Sale",
    "Office Desk Available",
    "Need Warehouse on Rent",
    "Furniture Combo Sale",
    "Buyer Needed for Plot",
]
areas = ["Anna Nagar", "T Nagar", "Velachery", "Adyar", "Porur", "Tambaram"]
contacts = [
    "9000000001",
    "9000000002",
    "9000000003",
    "9000000004",
    "9000000005",
]
listing_types = [
    BnsModel.LISTING_TYPE_BUYER,
    BnsModel.LISTING_TYPE_SELLER,
    BnsModel.LISTING_TYPE_RENTAL,
]


# Load optional images from media/marketplace/images
media_images_dir = os.path.join("media", "marketplace", "images")
available_images = []
if os.path.isdir(media_images_dir):
    for fname in os.listdir(media_images_dir):
        lower = fname.lower()
        if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
            available_images.append(f"marketplace/images/{fname}")


existing_slugs = set(BnsModel.objects.values_list("slug", flat=True))
new_slugs = set()


def make_unique_slug(title):
    base = slugify(title) or "marketplace-item"
    slug = base
    counter = 1
    while slug in existing_slugs or slug in new_slugs:
        counter += 1
        slug = f"{base}-{counter}"
    new_slugs.add(slug)
    return slug


base_time = timezone.now()
records = []
for i in range(RECORD_COUNT):
    title = f"{random.choice(titles)} #{i + 1}"
    min_price = random.randint(1000, 50000)
    max_price = min_price + random.randint(500, 20000)
    price = random.randint(min_price, max_price)

    record = BnsModel(
        title=title,
        slug=make_unique_slug(title),
        desc=f"Auto generated listing for {title}.",
        status=BnsModel.STATUS_PUBLISHED,
        listing_type=random.choice(listing_types),
        area=random.choice(areas),
        contact=random.choice(contacts),
        min_price=min_price,
        max_price=max_price,
        price=price,
        created_by=member_instance,
        created_by_username=member_instance.username,
        updated_by=member_instance,
        updated_by_username=member_instance.username,
        # Explicitly set published time to support time-based API navigation.
        published_at=base_time - timedelta(hours=i * HOURS_STEP),
        image=random.choice(available_images) if available_images else None,
    )
    records.append(record)


BnsModel.objects.bulk_create(records, batch_size=200)

print(f"Inserted {len(records)} marketplace records successfully.")
print(f"Published time range: newest={records[0].published_at}, oldest={records[-1].published_at}")
