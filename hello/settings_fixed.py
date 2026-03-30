"""
Django settings for hello project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent






# SECURITY
SECRET_KEY = 'django-insecure-change-this-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']


# -------------------------------
# APPLICATIONS
# -------------------------------
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
MEMBER_LOGIN_URL = os.getenv("MEMBER_LOGIN_URL", f"{FRONTEND_BASE_URL}/login/")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", BACKEND_BASE_URL)
PASSWORD_RESET_TOKEN_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "30"))

INSTALLED_APPS = [
    'rest_framework',
    'corsheaders',
    'adminlte4',
    'adminlte4_theme',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'member.apps.MemberConfig',
    'news',
    'home.apps.HomeConfig',
    'marketplace.apps.MarketplaceConfig',
    'donation.apps.DonationConfig',
]


# -------------------------------
# MIDDLEWARE
# -------------------------------

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'member.middleware.MemberAuthMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'hello.urls'

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True


# -------------------------------
# TEMPLATES
# -------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'myapplication'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'member.context_processors.sidebar_member',
            ],
        },
    },
]


WSGI_APPLICATION = 'hello.wsgi.application'


# -------------------------------
# DATABASE
# -------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 30,
        },
    }
}


# -------------------------------
# PASSWORD VALIDATION
# -------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# -------------------------------
# INTERNATIONAL
# -------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# -------------------------------
# STATIC / MEDIA
# -------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "http://127.0.0.1:8000")


# -------------------------------
# EMAIL
# -------------------------------

# Change these 2 values once; all email flows use them.
MAIL_ACCOUNT_EMAIL = os.getenv("MAIL_ACCOUNT_EMAIL", "neighbornett@gmail.com")
MAIL_ACCOUNT_APP_PASSWORD = os.getenv("MAIL_ACCOUNT_APP_PASSWORD", "fejflxbdsafwprdz")

# For Gmail SMTP, use an App Password in EMAIL_HOST_PASSWORD
# (regular Gmail account password will not work).
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('1', 'true', 'yes')
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '20'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', MAIL_ACCOUNT_EMAIL)
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', MAIL_ACCOUNT_APP_PASSWORD)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f"Community Portal <{MAIL_ACCOUNT_EMAIL}>")
REPLY_TO_EMAIL = os.getenv('REPLY_TO_EMAIL', MAIL_ACCOUNT_EMAIL)


# -------------------------------
# DEFAULT PK
# -------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# -------------------------------
# SESSION CONFIGURATION
# -------------------------------

# Session cookie settings for better cross-origin/IP support
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days in seconds
SESSION_COOKIE_DOMAIN = None  # Allow cookies on current domain (works with IP too)
SESSION_COOKIE_PATH = '/'
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = None  # Disabled for cross-origin/IP access

# CSRF cookie settings
CSRF_COOKIE_DOMAIN = None  # Allow cookies on current domain
CSRF_COOKIE_PATH = '/'
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = None  # Disabled for cross-origin/IP access

# -------------------------------
# LOGIN / LOGOUT
# -------------------------------

LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_REDIRECT_URL = '/admin/'
