import os
import django
import random
from faker import Faker
from datetime import date

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')  # your project name
django.setup()

from home.models import Member, MemberDetail, User1  # replace 'your_app' with your app name

fake = Faker()

# Make sure we have some Members and Users
members = list(Member.objects.all())
users = list(User1.objects.all())

if not members:
    print("No Member records found. Please create some Member records first.")
    exit()

if not users:
    print("No User1 records found. Please create some User1 records first.")
    exit()

gender_choices = ['M', 'F', 'O']

records_to_create = []

for _ in range(1000):
    dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
    age = date.today().year - dob.year
    
    record = MemberDetail(
        member_no=random.choice(members),
        first_name=fake.first_name(),
        middle_name=fake.first_name() if random.random() > 0.5 else None,
        surname=fake.last_name(),
        date_of_birth=dob,
        age=age,
        gender=random.choice(gender_choices),
        occupation=fake.job() if random.random() > 0.3 else None,
        created_by=random.choice(users),
        updated_by=random.choice(users),
    )
    records_to_create.append(record)

# Bulk insert for efficiency
MemberDetail.objects.bulk_create(records_to_create)
print("Inserted 1000 dummy MemberDetail records successfully!")
