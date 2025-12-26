# Settings Configuration Guide

This guide outlines the required settings for the Medical API project.

## Required Settings in `medical_api/settings.py`

### 1. Add mainAPI to INSTALLED_APPS

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    
    # Local apps
    'mainAPI',
]
```

### 2. Set Custom User Model

```python
AUTH_USER_MODEL = 'mainAPI.User'
```

### 3. Configure REST Framework

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### 4. Configure JWT

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### 5. Configure CORS

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Add this
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    # Add your frontend URLs here
]

CORS_ALLOW_CREDENTIALS = True
```

### 6. Configure Media Files

```python
import os

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
```

### 7. Configure Database (MySQL)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'medical_api',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

### 8. Security Settings (Production)

```python
# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Enable in production with HTTPS
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
```

### 9. API Documentation (drf-spectacular)

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'Medical Management API',
    'DESCRIPTION': 'University Healthcare Management System API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

### 10. Celery Configuration (for background tasks)

```python
# Celery settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Beat schedule (for auto-closing tickets)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'auto-close-inactive-tickets': {
        'task': 'mainAPI.tasks.auto_close_inactive_tickets',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
}
```

## Next Steps

1. **Update settings.py** with the above configurations
2. **Create migrations**: `python manage.py makemigrations`
3. **Run migrations**: `python manage.py migrate`
4. **Create superuser**: `python manage.py createsuperuser`
5. **Run development server**: `python manage.py runserver`

## Optional: Create Celery Tasks

Create `mainAPI/tasks.py` for background tasks:

```python
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from mainAPI.models import Ticket

@shared_task
def auto_close_inactive_tickets():
    """
    Auto-close tickets with no reply in 15 minutes
    """
    threshold = timezone.now() - timedelta(minutes=15)
    
    tickets = Ticket.objects.filter(
        status__in=['OPEN', 'IN_PROGRESS'],
        last_reply_at__lt=threshold
    )
    
    count = 0
    for ticket in tickets:
        ticket.close()
        count += 1
    
    return f"Auto-closed {count} tickets"
```

## Testing the API

You can test the endpoints using tools like:
- **Postman** or **Insomnia**
- **curl** commands
- **Swagger UI** at `/api/schema/swagger-ui/` (if configured with drf-spectacular)

Example login request:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "student1", "password": "password123"}'
```

## Troubleshooting

- If you get "No module named 'mainAPI'", make sure `mainAPI` is in `INSTALLED_APPS`
- If migrations fail, ensure `AUTH_USER_MODEL = 'mainAPI.User'` is set BEFORE running migrations
- For media file uploads, ensure the `media/` directory has proper write permissions
- Install `python-magic-bin` on Windows instead of `python-magic`
