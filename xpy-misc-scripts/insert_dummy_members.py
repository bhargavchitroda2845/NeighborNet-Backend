import os
import django
import random
from faker import Faker
from datetime import date

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from home.models import Member
from django.contrib.auth import get_user_model

fake = Faker()
User = get_user_model()

users = list(User.objects.all())
if not users:
    print("No User records found. Please create some users first.")
    exit()

gender_choices = ['M', 'F', 'O']
status_choices = ['Active', 'Inactive']

records_to_create = []

for _ in range(1000):
    dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
    age = date.today().year - dob.year

    username = fake.unique.user_name()
    phone_no = fake.unique.phone_number()

    # Plain text password for dummy data
    password = "password123"  

    member = Member(
        first_name=fake.first_name(),
        middle_name=fake.first_name() if random.random() > 0.5 else None,
        surname=fake.last_name(),
        phone_no=phone_no,
        date_of_birth=dob,
        age=age,
        gender=random.choice(gender_choices),
        occupation=fake.job() if random.random() > 0.3 else None,
        username=username,
        password=password,
        status=random.choice(status_choices),
        created_by=random.choice(users),
        updated_by=random.choice(users),
    )
    records_to_create.append(member)

Member.objects.bulk_create(records_to_create)
print("Inserted 1000 dummy Member records successfully!")
