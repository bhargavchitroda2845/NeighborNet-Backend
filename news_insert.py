from datetime import timedelta
import os
import random
import django
from django.utils import timezone
from django.utils.text import slugify

# Ensure Django is set up when running as a standalone script
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hello.settings")
django.setup()

from news.models import Category, News  # noqa: E402
from member.models import Member  # noqa: E402

# Replace with an actual member instance
member_instance = Member.objects.first()
if not member_instance:
    raise SystemExit("No Member found. Create a Member first, then rerun.")

# Define categories
categories = [
    "Births & Announcements",
    "Marriages & Engagements",
    "Achievements & Awards",
    "Obituaries & Condolences",
    "Housewarming & Property Updates",
    "Business Openings & Ventures",
    "Community Events & Get-Togethers",
    "Farewells & Retirements",
    "Health & Wellbeing Updates",
    "Education Milestones"
]

# Create categories if they don't exist
category_objs = {}
for cat_name in categories:
    category, created = Category.objects.get_or_create(name=cat_name)
    category_objs[cat_name] = category

# Load available images from media/news/images
media_images_dir = os.path.join("media", "news", "images")
available_images = []
if os.path.isdir(media_images_dir):
    for fname in os.listdir(media_images_dir):
        lower = fname.lower()
        if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
            available_images.append(f"news/images/{fname}")

# Generate 10 posts per category
news_posts = []
base_date = timezone.now()

sample_titles = {
    "Births & Announcements": [
        "Welcome Baby Arya!",
        "It’s a Boy! Baby Krishna Arrives",
        "Twin Joy: Anaya and Aarav Born",
        "New Arrival in Sharma Family",
        "Baby Naming Ceremony of Rohan",
        "Congratulations to Priya for Baby Girl",
        "Baby Shower Celebration for Meera",
        "Baby Boy Born to Verma Family",
        "Joyful Arrival of Baby Twins",
        "Little Miracle: Baby Arjun"
    ],
    "Marriages & Engagements": [
        "Anjali and Rohan Tie the Knot",
        "Engagement of Priya & Aman",
        "Wedding Bells for Kavya and Sameer",
        "Sangeet Ceremony of Meera & Arjun",
        "Reception Party for Ritu & Rahul",
        "Community Celebrates Wedding of Nisha & Vivek",
        "Engagement Celebration: Simran & Aditya",
        "Shaadi of Ananya & Raghav",
        "Marriage Anniversary Celebration of Seema & Karan",
        "Couple Ties Knot in Grand Ceremony"
    ],
    "Achievements & Awards": [
        "Rohit Wins Math Olympiad",
        "Priya Secures 1st Rank in College",
        "Meera Recognized for Community Service",
        "Arjun Bags Sports Championship",
        "Kavya Achieves Certification in Yoga",
        "Rahul Awarded Employee of the Month",
        "Simran Wins Singing Competition",
        "Vivek Receives Local Hero Award",
        "Ananya Completes Marathon Successfully",
        "Nisha Recognized for Volunteering"
    ],
    "Obituaries & Condolences": [
        "Condolences to Sharma Family",
        "Passing of Mr. Rajesh Verma",
        "Tribute to Late Mrs. Sunita Kapoor",
        "Remembering Community Elder Mr. Ramesh",
        "Obituary: Mrs. Anita Mehra",
        "Sad Demise of Mr. Suresh Patil",
        "Farewell to Mr. Vinod Joshi",
        "Condolence Message for Gupta Family",
        "Passing of Mrs. Rekha Singh",
        "Remembering Late Mr. Mahesh Kumar"
    ],
    "Housewarming & Property Updates": [
        "New Home for Sharma Family",
        "Housewarming Ceremony of Meera & Arjun",
        "Rohan Moves into New Apartment",
        "Community Welcomes New Residents",
        "Anjali Hosts Housewarming Party",
        "New Villa Inauguration by Verma Family",
        "Kavya Renovates Her Home",
        "Rahul Buys New Property",
        "Nisha Hosts Home Celebration",
        "Arjun Completes Interior Decoration"
    ],
    "Business Openings & Ventures": [
        "New Grocery Store by Sharma Family",
        "Bakery Launch by Meera",
        "Cafe Opening: Coffee & Co.",
        "Rohan Starts Digital Marketing Agency",
        "New Tailor Shop Opens in Community",
        "Priya Opens Yoga Studio",
        "Bookstore Inauguration by Kavya",
        "Rahul Opens Fitness Center",
        "Vivek Launches Tech Startup",
        "Nisha Opens Flower Boutique"
    ],
    "Community Events & Get-Togethers": [
        "Annual Community Picnic",
        "Festive Diwali Celebration",
        "Ganesh Chaturthi Gathering",
        "Neighborhood Holi Party",
        "Sports Day Event for Members",
        "Charity Drive in the Community",
        "Monthly Community Meeting",
        "Cultural Night Event",
        "Potluck Dinner Organized",
        "Community Talent Show"
    ],
    "Farewells & Retirements": [
        "Farewell Party for Mr. Ramesh",
        "Retirement Celebration for Mrs. Sunita",
        "Goodbye to Rahul on Transfer",
        "Farewell to Kavya Leaving the Community",
        "Retirement of Community Elder Mr. Rajesh",
        "Goodbye Gathering for Priya",
        "Farewell Lunch for Arjun",
        "Honoring Retirement of Mr. Vinod",
        "Farewell Ceremony for Nisha",
        "Community Sends Off Ananya"
    ],
    "Health & Wellbeing Updates": [
        "Community Yoga Camp by Kavya",
        "Blood Donation Drive Organized",
        "Health Awareness Workshop",
        "Meera Recovers After Surgery",
        "Vaccination Camp for Members",
        "Fitness Challenge Launched",
        "Wellness Seminar Conducted",
        "Arjun Achieves Personal Fitness Goal",
        "Mental Health Workshop by Priya",
        "Community Marathon Event"
    ],
    "Education Milestones": [
        "Rohit Graduates from University",
        "Priya Completes Course in AI",
        "Meera Receives Scholarship",
        "Arjun Finishes High School",
        "Kavya Wins Science Fair",
        "Rahul Passes Competitive Exam",
        "Simran Completes Internship",
        "Vivek Receives Academic Award",
        "Ananya Graduates with Honors",
        "Nisha Completes Art Workshop"
    ]
}

# Prepare unique slug set (existing + new)
existing_slugs = set(News.objects.values_list("slug", flat=True))
new_slugs = set()

def make_unique_slug(title):
    base = slugify(title) or "news"
    slug = base
    counter = 1
    while slug in existing_slugs or slug in new_slugs:
        counter += 1
        slug = f"{base}-{counter}"
    new_slugs.add(slug)
    return slug

# Generate News objects
for category_name, titles in sample_titles.items():
    category = category_objs[category_name]
    for i, title in enumerate(titles):
        random_image = random.choice(available_images) if available_images else None
        news = News(
            title=title,
            slug=make_unique_slug(title),
            content=f"Content for {title} in {category_name}.",
            category=category,
            status="published",
            published_at=base_date - timedelta(days=i),
            created_by=member_instance,
            updated_by=member_instance,
            image=random_image,
        )
        news_posts.append(news)

# Bulk insert
News.objects.bulk_create(news_posts)
print(f"Inserted {len(news_posts)} news posts successfully!")
