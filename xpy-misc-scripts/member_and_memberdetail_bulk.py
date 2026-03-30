import os
import django
import random
from faker import Faker
from datetime import date

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from home.models import Member, MemberDetail
from django.contrib.auth import get_user_model

fake = Faker('en_IN')  # Indian names
User = get_user_model()

# Fetch existing users
users = list(User.objects.all())
if not users:
    print("No User records found. Please create some users first.")
    exit()

# Choices
gender_choices = ['M', 'F', 'O']
status_choices = ['Active', 'Inactive']
occupation_choices = ['Service', 'Business', 'Education', None]

def random_age_group():
    """Randomly assign age group for MemberDetail."""
    group = random.choices(
        ['Kid', 'Adult', 'Elder'],
        weights=[0.2, 0.6, 0.2],  # more adults
        k=1
    )[0]
    
    if group == 'Kid':
        age = random.randint(0, 17)
    elif group == 'Adult':
        age = random.randint(18, 59)
    else:
        age = random.randint(60, 90)
    return age

# --- Step 1: Generate Members ---
num_members = 400
members_to_create = []

for _ in range(num_members):
    dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
    age = date.today().year - dob.year
    username = fake.unique.user_name()
    phone_no = fake.unique.phone_number()
    member = Member(
        first_name=fake.first_name(),
        middle_name=fake.first_name() if random.random() > 0.5 else None,
        surname=fake.last_name(),
        phone_no=phone_no,
        date_of_birth=dob,
        age=age,
        gender=random.choice(gender_choices),
        occupation=random.choice(occupation_choices),
        username=username,
        password="password123",
        status=random.choice(status_choices),
        created_by=random.choice(users),
        updated_by=random.choice(users),
    )
    members_to_create.append(member)

Member.objects.bulk_create(members_to_create)
print(f"Inserted {num_members} dummy Member records successfully!")

# Fetch newly created members
members = list(Member.objects.all())

# --- Step 2: Generate MemberDetail linked to Members ---
member_detail_records = []

for member in members:
    num_details = random.randint(2, 9)
    for _ in range(num_details):
        age = random_age_group()
        dob = date.today().replace(year=date.today().year - age)
        member_detail = MemberDetail(
            member_no=member,
            first_name=fake.first_name(),
            middle_name=fake.first_name() if random.random() > 0.5 else None,
            surname=fake.last_name(),
            date_of_birth=dob,
            age=age,
            gender=random.choice(gender_choices),
            occupation=random.choice(occupation_choices),
            created_by=random.choice(users),
            updated_by=random.choice(users),
        )
        member_detail_records.append(member_detail)

MemberDetail.objects.bulk_create(member_detail_records)
print(f"Inserted {len(member_detail_records)} dummy MemberDetail records successfully!")
