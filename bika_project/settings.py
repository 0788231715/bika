"""
Django settings for bika_project project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-bika-project-secret-key-2024'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'crispy_forms',
    
    # Local apps
    'bika',

]

# Crispy Forms configuration - USING BOOTSTRAP4 (more stable)
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bika_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'bika.context_processors.site_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'bika_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static',
                    BASE_DIR / "static",]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_ROOT = BASE_DIR / "staticfiles"
# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs

LOGIN_REDIRECT_URL = 'bika:admin_dashboard'  # Redirect to your custom dashboard
LOGOUT_REDIRECT_URL = 'bika:home'  # Redirect to home after logout
LOGIN_URL = 'bika:login'

# Email configuration (for password reset)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # For development
# For production, use:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'your-smtp-host'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'abeliniyigena@gmail.com'
# EMAIL_HOST_PASSWORD = 'MUGO12ruku__'
# DEFAULT_FROM_EMAIL = 'Bika <noreply@bika.com>'

AUTH_USER_MODEL = 'bika.CustomUser'
# Stripe Configuration (if using payments)
STRIPE_PUBLISHABLE_KEY = 'your_publishable_key_here'
STRIPE_SECRET_KEY = 'your_secret_key_here'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Create required directories
os.makedirs(os.path.join(MEDIA_ROOT, 'trained_models'), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'datasets'), exist_ok=True)