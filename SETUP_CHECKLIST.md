# Implementation Checklist & Next Steps

## ✅ Completed Tasks

- [x] Created custom permission classes in `mainAPI/permissions.py`
- [x] Created serializers directory with all serializers:
  - [x] User & Patient serializers
  - [x] Appointment serializers
  - [x] Examination serializers
  - [x] Ticket & TicketReply serializers
  - [x] Image upload serializers
- [x] Created views directory with all views:
  - [x] Authentication view (login)
  - [x] User profile views
  - [x] Patient lookup views (QR scan)
  - [x] Appointment management views
  - [x] Examination workflow views
  - [x] Ticket system views
  - [x] Image upload view
- [x] Set up URL routing (mainAPI/urls.py and medical_api/urls.py)
- [x] Updated requirements.txt with all dependencies
- [x] Created Celery configuration
- [x] Created background tasks (auto-close tickets)
- [x] Created comprehensive documentation

## 📋 Required Configuration Steps

### 1. Install Dependencies

```bash
cd /home/ubuntu/code/medical_api
pip install -r requirements.txt
```

### 2. Update Django Settings

Edit `medical_api/settings.py` and add/update the following:

#### a. Set Custom User Model (CRITICAL - Do this BEFORE migrations)

```python
AUTH_USER_MODEL = 'mainAPI.User'
```

#### b. Update INSTALLED_APPS

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

#### c. Update MIDDLEWARE (add CORS)

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Add this line
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

#### d. Add REST Framework Configuration

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

#### e. Add JWT Configuration

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

#### f. Add CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
]
CORS_ALLOW_CREDENTIALS = True
```

#### g. Add Media Files Configuration

```python
import os

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
```

#### h. Configure Database (if using MySQL)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'medical_api',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
```

#### i. Add Celery Configuration

```python
# Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Celery Beat
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'auto-close-tickets': {
        'task': 'mainAPI.tasks.auto_close_inactive_tickets',
        'schedule': crontab(minute='*/15'),
    },
}
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 5. Create Test Data (Optional)

You can use Django shell to create test users:

```bash
python manage.py shell
```

```python
from mainAPI.models import User, PatientProfile, DoctorProfile

# Create a student (patient)
student = User.objects.create_user(
    username='student1',
    email='student1@university.edu',
    password='password123',
    full_name='John Doe',
    student_id='STU001',
    role='STUDENT'
)
PatientProfile.objects.create(
    user=student,
    blood_type='A+',
    allergies='Peanuts, Penicillin'
)

# Create a doctor
doctor = User.objects.create_user(
    username='doctor1',
    email='doctor1@university.edu',
    password='password123',
    full_name='Dr. Jane Smith',
    role='DOCTOR'
)
DoctorProfile.objects.create(
    user=doctor,
    specialization='General Medicine',
    department='Healthcare'
)
```

### 6. Run Development Server

```bash
python manage.py runserver
```

Visit: http://localhost:8000/api/v1/

### 7. Test the API

#### Login as student:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "password": "password123"
  }'
```

Copy the token from the response, then test authenticated endpoints:

```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 8. Run Celery (Optional - for background tasks)

In separate terminal windows:

**Terminal 1 - Celery Worker:**
```bash
celery -A medical_api worker -l info
```

**Terminal 2 - Celery Beat:**
```bash
celery -A medical_api beat -l info
```

## 🔍 Verification Checklist

After completing the steps above, verify:

- [ ] All dependencies installed without errors
- [ ] `AUTH_USER_MODEL` is set in settings.py
- [ ] Migrations run successfully
- [ ] Superuser created
- [ ] Development server starts without errors
- [ ] Login endpoint works (returns JWT token)
- [ ] Authenticated endpoints require token
- [ ] Media directory exists and is writable
- [ ] No import errors in console

## 📚 Documentation References

- **SETTINGS_GUIDE.md** - Detailed settings configuration
- **README_IMPLEMENTATION.md** - Project overview and architecture
- **api.yaml** - API specification
- **plan/model.md** - Database models documentation
- **plan/view.md** - Views architecture documentation
- **plan/security_outline.md** - Security requirements

## 🐛 Common Issues & Solutions

### Issue: "No module named 'rest_framework'"
**Solution:** Run `pip install -r requirements.txt`

### Issue: "AUTH_USER_MODEL not set"
**Solution:** Add `AUTH_USER_MODEL = 'mainAPI.User'` to settings.py BEFORE running migrations

### Issue: "Table 'mainAPI_user' doesn't exist"
**Solution:** Run migrations: `python manage.py migrate`

### Issue: "Cannot import name 'celery_app'"
**Solution:** The celery import is already added to `medical_api/__init__.py` - just restart the server

### Issue: python-magic fails on Windows
**Solution:** Install `python-magic-bin` instead: `pip install python-magic-bin`

### Issue: Media files 404
**Solution:** Ensure `MEDIA_URL` and `MEDIA_ROOT` are configured in settings.py

## 🎯 Next Development Tasks

After basic setup is complete:

1. **Write Unit Tests**
   - Test each viewset
   - Test serializers
   - Test permissions
   - Test audit logging

2. **API Documentation**
   - Configure drf-spectacular
   - Generate OpenAPI schema
   - Set up Swagger UI

3. **Frontend Integration**
   - Configure CORS for frontend URLs
   - Test endpoints from frontend
   - Handle authentication flow

4. **Production Preparation**
   - Enable security settings (HTTPS, HSTS)
   - Configure production database
   - Set up static/media file serving (S3, CDN)
   - Configure logging
   - Set up monitoring

5. **Additional Features**
   - Rate limiting implementation
   - Advanced search/filtering
   - Pagination optimization
   - Caching strategy
   - Email notifications

## 📞 Support

Refer to the documentation files in this project for detailed information about each component.

---

**Implementation Status**: ✅ Complete - Ready for Configuration
**Last Updated**: December 26, 2025
