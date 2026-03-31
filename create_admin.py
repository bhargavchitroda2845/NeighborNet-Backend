import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hello.settings')
django.setup()

from django.contrib.auth import get_user_model

# Default superuser credentials
username = os.environ.get('ADMIN_USERNAME', 'admin')
password = os.environ.get('ADMIN_PASSWORD', 'Password123')
email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

User = get_user_model()

if not User.objects.filter(username=username).exists():
    try:
        User.objects.create_superuser(username, email, password)
        print(f"Superuser '{username}' created successfully!")
    except Exception as e:
        print(f"Error creating superuser: {e}")
else:
    print(f"Superuser '{username}' already exists.")
