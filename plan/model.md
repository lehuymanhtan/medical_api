# Django Models Plan - Medical Management System

## Overview
This document outlines the Django models architecture for the University Healthcare Management System based on the API specification (api.yaml v1.0.0).

## Core Design Principles
- **RBAC (Role-Based Access Control)**: Student, Doctor, Admin
- **UUID Primary Keys**: For security and QR code generation
- **Audit Trail**: Track creation and modification timestamps
- **Soft Deletes**: Where applicable for data integrity
- **Status Management**: Proper state transitions for appointments and tickets

---

## Models Architecture

### 1. User Model (Custom User)
**Purpose**: Authentication and base user information

```python
class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser
    Supports RBAC with three roles
    """
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        DOCTOR = 'DOCTOR', 'Doctor'
        ADMIN = 'ADMIN', 'Admin'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices)
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # QR Code is generated from UUID (id field)
```

**Key Points**:
- UUID `id` is used for QR code generation (`/patients/lookup?qr_code={uuid}`)
- `student_id` only for STUDENT role
- Role determines access permissions
- Extends Django's AbstractUser for authentication features

---

### 2. PatientProfile Model
**Purpose**: Medical information for patients (Students only)

```python
class PatientProfile(models.Model):
    """
    Extended medical profile for users with patient role
    One-to-One with User model
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    
    # Medical Information
    blood_type = models.CharField(max_length=5, choices=[
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ], blank=True)
    
    allergies = models.TextField(blank=True, help_text="Comma-separated list of allergies")
    chronic_conditions = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Key Points**:
- Linked to User with role STUDENT
- Supports `/users/me/medical-summary` endpoint
- Allergies stored as text (can be normalized to separate table if needed)

---

### 3. DoctorProfile Model
**Purpose**: Professional information for doctors

```python
class DoctorProfile(models.Model):
    """
    Extended profile for users with doctor role
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    
    specialization = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Key Points**:
- Linked to User with role DOCTOR or ADMIN
- Supports doctor workflow endpoints
- Simplified profile for small clinic/school setting

---

### 4. Appointment Model
**Purpose**: Date reservation system for medical visits

```python
class Appointment(models.Model):
    """
    Appointment booking - date-only registration for medical visits
    Doctor assigned later by admin/system
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='patient_appointments',
        limit_choices_to={'role': 'STUDENT'}
    )
    
    appointment_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField()
    
    # Cancellation
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_appointments')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-appointment_date']
        indexes = [
            models.Index(fields=['patient', 'appointment_date']),
            models.Index(fields=['status', 'appointment_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['patient', 'appointment_date'],
                condition=models.Q(status__in=['PENDING', 'COMPLETED']),
                name='one_appointment_per_patient_per_day'
            )
        ]
```

**Key Points**:
- Supports endpoints: `GET /appointments`, `POST /appointments`, `PATCH /appointments/{id}`
- Status workflow: PENDING → COMPLETED/CANCELLED
- Date-only booking (no specific time slots)
- No doctor assignment - doctor selected when creating examination
- One appointment per patient per day constraint
- Simple registration system for medical visit dates

---

### 5. Examination Model
**Purpose**: Medical examination records (core clinical data)

```python
class Examination(models.Model):
    """
    Medical examination record
    Immutable once finalized (COMPLETED status)
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        COMPLETED = 'COMPLETED', 'Completed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='examinations',
        limit_choices_to={'role': 'STUDENT'}
    )
    doctor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='conducted_examinations',
        limit_choices_to={'role__in': ['DOCTOR', 'ADMIN']}
    )
    appointment = models.OneToOneField(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='examination',
        null=True,
        blank=True
    )
    
    # Examination Data
    symptoms = models.TextField(blank=True)
    initial_diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Final (Locked after finalize)
    final_diagnosis = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    
    # Vital Signs
    blood_pressure = models.CharField(max_length=20, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    examination_date = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-examination_date']
        indexes = [
            models.Index(fields=['patient', '-examination_date']),
            models.Index(fields=['doctor', '-examination_date']),
        ]
```

**Key Points**:
- Supports endpoints: `POST /examinations`, `PUT /examinations/{id}`, `POST /examinations/{id}/finalize`
- DRAFT status allows updates, COMPLETED is immutable
- `finalized_at` set when status changes to COMPLETED
- Linked to Appointment (one examination per appointment)
- Provides data for `/users/me/examinations` and `/patients/{id}/examinations`

---

### 6. Ticket Model
**Purpose**: Support ticket system from students to doctors

```python
class Ticket(models.Model):
    """
    Support ticket system for students to communicate with doctors
    """
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        PENDING = 'PENDING', 'Pending Response'
        RESOLVED = 'RESOLVED', 'Resolved'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tickets',
        limit_choices_to={'role': 'STUDENT'}
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_tickets',
        limit_choices_to={'role__in': ['DOCTOR', 'ADMIN']}
    )
    
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    
    # Optional link to appointment
    related_appointment = models.ForeignKey(
        Appointment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tickets'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    last_reply_at = models.DateTimeField(null=True, blank=True)
    
    # Auto-close logic: close if no reply in 15 minutes
    auto_close_threshold_minutes = 15
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creator', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
```

**Key Points**:
- Supports endpoints: `GET /tickets`, `POST /tickets`, `GET /tickets/{id}`, `POST /tickets/{id}/close`
- Auto-close feature if no reply within 15 minutes (needs background task/celery)
- Can be linked to an appointment
- Assignment system for doctors/admins

---

### 7. TicketReply Model
**Purpose**: Conversation thread for tickets

```python
class TicketReply(models.Model):
    """
    Reply/message in a ticket conversation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_replies')
    
    content = models.TextField()
    is_staff_reply = models.BooleanField(default=False)
    
    # Attachments
    attachment_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Ticket replies'
```

**Key Points**:
- Supports endpoint: `POST /tickets/{id}/replies`
- `is_staff_reply` automatically set based on author's role (DOCTOR/ADMIN)
- Part of `TicketDetail` schema response
- Updates parent ticket's `last_reply_at` on save

---

### 8. UploadedFile Model
**Purpose**: Track uploaded images only

```python
class UploadedFile(models.Model):
    """
    Track uploaded image files only (.jpg, .jpeg, .png)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    
    file = models.ImageField(upload_to='uploads/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100, choices=[
        ('image/jpeg', 'JPEG'),
        ('image/png', 'PNG'),
    ])
    
    url = models.URLField()
    
    # Optional associations
    examination = models.ForeignKey(
        Examination, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='attachments'
    )
    ticket_reply = models.ForeignKey(
        TicketReply,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
```

**Key Points**:
- Supports endpoint: `POST /upload/image`
- Image-only storage (.jpg, .jpeg, .png)
- Optional linking to examinations or ticket replies
- Returns URL in response (`ImageUploadResponse` schema)
- File stored with date-based path organization
- Uses Django's ImageField with validation

---

### 9. AuditLog Model
**Purpose**: Track sensitive operations for compliance and security

```python
class AuditLog(models.Model):
    """
    Comprehensive audit trail for sensitive operations
    Tracks all critical actions in the system
    """
    class Action(models.TextChoices):
        # Examination actions
        EXAMINATION_CREATED = 'EXAMINATION_CREATED', 'Examination Created'
        EXAMINATION_UPDATED = 'EXAMINATION_UPDATED', 'Examination Updated'
        EXAMINATION_FINALIZED = 'EXAMINATION_FINALIZED', 'Examination Finalized'
        
        # Appointment actions
        APPOINTMENT_CREATED = 'APPOINTMENT_CREATED', 'Appointment Created'
        APPOINTMENT_CANCELLED = 'APPOINTMENT_CANCELLED', 'Appointment Cancelled'
        APPOINTMENT_COMPLETED = 'APPOINTMENT_COMPLETED', 'Appointment Completed'
        
        # Ticket actions
        TICKET_CREATED = 'TICKET_CREATED', 'Ticket Created'
        TICKET_CLOSED = 'TICKET_CLOSED', 'Ticket Closed'
        TICKET_ASSIGNED = 'TICKET_ASSIGNED', 'Ticket Assigned'
        
        # Data access
        PATIENT_RECORD_ACCESSED = 'PATIENT_RECORD_ACCESSED', 'Patient Record Accessed'
        PATIENT_HISTORY_VIEWED = 'PATIENT_HISTORY_VIEWED', 'Patient History Viewed'
        QR_SCAN_LOOKUP = 'QR_SCAN_LOOKUP', 'QR Code Patient Lookup'
        
        # User actions
        USER_LOGIN = 'USER_LOGIN', 'User Login'
        USER_LOGOUT = 'USER_LOGOUT', 'User Logout'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=Action.choices)
    
    # Target object info
    model_name = models.CharField(max_length=100)
    object_id = models.UUIDField(null=True, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    
    # Change details
    changes = models.JSONField(default=dict, blank=True)
    additional_data = models.JSONField(default=dict, blank=True)
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['-timestamp']),
        ]
```

**Key Points**:
- Comprehensive tracking of all sensitive operations
- Records examination finalization (immutable record creation)
- Tracks appointment lifecycle (creation, cancellation, completion)
- Monitors ticket activities (creation, closure, assignment)
- Logs patient data access (QR scans, history views, record access)
- Stores change details in JSON format
- Captures request metadata (IP, user agent)
- Cannot be deleted or modified (append-only log)
- Used for compliance, security audits, and debugging

---

## Additional Considerations

### 1. TimeSlot Model (Optional - For Scheduling)
```python
class TimeSlot(models.Model):
    """
    Available time slots for doctor scheduling
    Admin/Super Doctor can manage these
    """
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_slots')
    day_of_week = models.IntegerField(choices=[(i, calendar.day_name[i]) for i in range(7)])
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
```

**Note**: Not critical for initial implementation since appointments are manually arranged.

---

## Model Relationships Summary

```
User (1) ←→ (1) PatientProfile [STUDENT only]
User (1) ←→ (1) DoctorProfile [DOCTOR/ADMIN only]
User (1) ←→ (N) Appointment (as patient) [STUDENT only]
User (1) ←→ (N) Examination (as patient) [STUDENT only]
User (1) ←→ (N) Examination (as doctor) [DOCTOR/ADMIN only]
User (1) ←→ (N) Ticket (as creator) [STUDENT only]
User (1) ←→ (N) Ticket (as assigned_to) [Optional, DOCTOR/ADMIN]
User (1) ←→ (N) TicketReply
User (1) ←→ (N) UploadedFile
User (1) ←→ (N) AuditLog

Appointment (1) ←→ (1) Examination
Appointment (1) ←→ (N) Ticket

Ticket (1) ←→ (N) TicketReply

Examination (1) ←→ (N) UploadedFile
TicketReply (1) ←→ (N) UploadedFile
```

---

## Permissions & Business Rules

### User Permissions Matrix

| Action | Student | Doctor | Admin |
|--------|---------|--------|-------|
| View own profile | ✓ | ✓ | ✓ |
| View own medical summary | ✓ | - | - |
| Create appointment | ✓ | - | - |
| View own appointments | ✓ | ✓ | ✓ |
| Cancel own appointment | ✓ | - | - |
| Scan QR & lookup patient | - | ✓ | ✓ |
| View patient history | - | ✓ | ✓ |
| Create examination | - | ✓ | ✓ |
| Finalize examination | - | ✓ | ✓ |
| Create ticket | ✓ | - | - |
| Reply to ticket | - | ✓ | ✓ |
| Assign tickets | - | - | ✓ |

### Business Logic Rules

1. **Appointment Creation**:
   - Student registers for a date (no doctor selection)
   - One appointment per student per day (database constraint)
   - Default status: PENDING
   - `reason` field is required
   - Status workflow: PENDING → COMPLETED or CANCELLED
   - Doctor selected when creating examination record

2. **Examination Workflow**:
   - Created when doctor sees patient
   - DRAFT allows updates
   - Finalize is irreversible (locks record)
   - Must have final_diagnosis and prescription to finalize
   - Triggers audit log entry on finalization

3. **Ticket System**:
   - Only students can create tickets
   - Assigned to doctor/admin (optional, can be assigned later)
   - Auto-close: Background job checks `last_reply_at`
   - If > 15 minutes and status != RESOLVED, auto-close
   - Can be linked to an appointment for context

4. **QR Code Lookup**:
   - QR contains user UUID
   - Only doctors/admins can access `/patients/lookup`
   - Returns patient summary with last diagnosis
   - Creates audit log entry for access tracking

5. **File Upload Security**:
   - Images only: .jpg, .jpeg, .png
   - Max file size limit (10MB)
   - Store with UUID filename
   - Validate MIME type on upload
   - Serve via secure URL

6. **Audit Trail**:
   - All sensitive operations logged automatically
   - Cannot be deleted or modified
   - Includes IP address and user agent
   - Retention policy for compliance

---

## Database Indexes

**Critical indexes** (in addition to those defined in models):

```python
# User model
indexes = [
    models.Index(fields=['email']),
    models.Index(fields=['student_id']),
    models.Index(fields=['role', 'is_active']),
]

# Appointment model
indexes = [
    models.Index(fields=['appointment_date', 'status']),
    models.Index(fields=['patient', 'appointment_date']),
]

# Examination model
indexes = [
    models.Index(fields=['status', 'examination_date']),
]

# AuditLog model
indexes = [
    models.Index(fields=['user', '-timestamp']),
    models.Index(fields=['action', '-timestamp']),
    models.Index(fields=['model_name', 'object_id']),
    models.Index(fields=['-timestamp']),
]
```

---

## Migration Strategy

### Phase 1: Core Models
1. Custom User model
2. PatientProfile & DoctorProfile
3. Appointment (with unique constraint)

### Phase 2: Clinical Features
4. Examination
5. UploadedFile

### Phase 3: Support System
6. Ticket
7. TicketReply

### Phase 4: Compliance & Auditing
8. AuditLog
9. TimeSlot (optional)

**Important**: Custom User model must be created FIRST before any migrations.

---

## API Endpoint → Model Mapping

| Endpoint | Primary Model | Related Models |
|----------|--------------|----------------|
| `/auth/login` | User | - |
| `/users/me` | User | PatientProfile, DoctorProfile |
| `/users/me/medical-summary` | PatientProfile | Examination (for last_visit) |
| `/users/me/examinations` | Examination | User, Doctor |
| `/patients/lookup` | User (via QR) | PatientProfile, Examination |
| `/patients/{id}/examinations` | Examination | User |
| `/appointments` | Appointment | User, Doctor |
| `/appointments/{id}` | Appointment | - |
| `/examinations` | Examination | User, Appointment |
| `/examinations/{id}` | Examination | - |
| `/examinations/{id}/finalize` | Examination | - |
| `/tickets` | Ticket | User |
| `/tickets/{id}` | Ticket | TicketReply |
| `/tickets/{id}/close` | Ticket | - |
| `/tickets/{id}/replies` | TicketReply | Ticket, User |
| `/upload/image` | UploadedFile | User |

---

## Settings & Configuration

### Required Settings

```python
# settings.py

AUTH_USER_MODEL = 'mainAPI.User'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'medical_api',
        'USER': 'your_mysql_user',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# File upload
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# Celery (for auto-close tickets)
CELERY_BEAT_SCHEDULE = {
    'auto-close-tickets': {
        'task': 'mainAPI.tasks.auto_close_inactive_tickets',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

---

## Next Steps

1. **Create models.py** based on this plan
2. **Setup custom User model** in settings.py
3. **Create initial migration**: `python manage.py makemigrations`
4. **Apply migrations**: `python manage.py migrate`
5. **Create serializers** for Django REST Framework
6. **Implement ViewSets** following RBAC rules
7. **Setup JWT authentication**
8. **Add URL routing** matching API spec
9. **Write tests** for each endpoint
10. **Setup Celery** for background tasks

---

## Technical Stack Recommendations

- **Django**: 4.2+ (LTS)
- **Django REST Framework**: 3.14+
- **djangorestframework-simplejwt**: For JWT auth
- **Pillow**: For image handling
- **Celery + Redis**: For background tasks (ticket auto-close)
- **MySQL**: Production database (with utf8mb4 charset for full Unicode support)
- **mysqlclient**: MySQL database adapter for Django
- **django-cors-headers**: For frontend integration
- **drf-spectacular**: For OpenAPI schema generation

---

## Security Considerations

1. **Authentication**: JWT with refresh tokens
2. **Authorization**: Django permissions + custom RBAC decorators
3. **Data Access**: Row-level permissions (patients can only see their data)
4. **QR Security**: UUIDs are non-sequential, rate limit lookup endpoint
5. **File Upload**: Validate MIME types, scan for malware
6. **Audit Trail**: Log all sensitive operations
7. **HIPAA Compliance**: Encrypt sensitive fields, secure backups
8. **API Rate Limiting**: Prevent abuse (django-ratelimit)

---

*Generated: 2025-12-25*
*Based on: API Specification v1.0.0 (api.yaml)*
