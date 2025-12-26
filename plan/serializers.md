# Django REST Framework Serializers Plan - Medical Management System

## Overview
This document outlines the serializer architecture for the University Healthcare Management System based on the models design and API specification (api.yaml v1.0.0).

## Core Design Principles
- **Role-Based Serialization**: Different fields exposed based on user role
- **Input/Output Separation**: Separate serializers for write vs read operations
- **Nested Serializers**: For related data without N+1 queries
- **Validation**: Field-level and object-level validation
- **Read-Only Fields**: Enforce immutability where required
- **Minimal Data Exposure**: Only expose necessary fields per endpoint

---

## Serializer Architecture

### 1. User Serializers

#### 1.1 UserSerializer (Base)
**Purpose**: Basic user information for general contexts

```python
class UserSerializer(serializers.ModelSerializer):
    """
    Basic user serializer for nested representations
    """
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'role']
        read_only_fields = ['id', 'role']
```

**Usage**: Nested in other serializers (appointment creator, examination doctor, etc.)

---

#### 1.2 CurrentUserSerializer
**Purpose**: `/users/me` endpoint - authenticated user's profile

```python
class CurrentUserSerializer(serializers.ModelSerializer):
    """
    Full user profile with role-specific nested data
    Maps to UserProfile schema in API spec
    """
    patient_profile = serializers.SerializerMethodField()
    doctor_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'phone_number', 
            'role', 'student_id', 'created_at',
            'patient_profile', 'doctor_profile'
        ]
        read_only_fields = ['id', 'role', 'created_at']
    
    def get_patient_profile(self, obj):
        if obj.role == User.Role.STUDENT and hasattr(obj, 'patient_profile'):
            return PatientProfileSerializer(obj.patient_profile).data
        return None
    
    def get_doctor_profile(self, obj):
        if obj.role in [User.Role.DOCTOR, User.Role.ADMIN] and hasattr(obj, 'doctor_profile'):
            return DoctorProfileSerializer(obj.doctor_profile).data
        return None
```

**Key Points**:
- Conditionally includes patient_profile or doctor_profile
- Maps to `UserProfile` schema
- Read-only `id`, `role`, `created_at`

---

#### 1.3 PatientProfileSerializer
**Purpose**: Medical information for students

```python
class PatientProfileSerializer(serializers.ModelSerializer):
    """
    Patient medical profile information
    Nested in CurrentUserSerializer
    """
    class Meta:
        model = PatientProfile
        fields = [
            'blood_type', 'allergies', 'chronic_conditions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_allergies(self, value):
        """Ensure allergies is properly formatted"""
        if value:
            # Clean up comma-separated list
            allergies = [a.strip() for a in value.split(',') if a.strip()]
            return ', '.join(allergies)
        return value
```

**Key Points**:
- Updatable by patient (student)
- Validates allergy format
- Part of `UserProfile` schema

---

#### 1.4 DoctorProfileSerializer
**Purpose**: Professional information for doctors

```python
class DoctorProfileSerializer(serializers.ModelSerializer):
    """
    Doctor professional profile information
    Nested in CurrentUserSerializer
    """
    class Meta:
        model = DoctorProfile
        fields = [
            'specialization', 'department', 'bio',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
```

**Key Points**:
- Part of `UserProfile` schema
- Updatable by doctor/admin

---

#### 1.5 MedicalSummarySerializer
**Purpose**: `/users/me/medical-summary` endpoint

```python
class MedicalSummarySerializer(serializers.Serializer):
    """
    Medical summary for patient
    Maps to MedicalSummary schema in API spec
    """
    patient_id = serializers.UUIDField(source='user.id')
    full_name = serializers.CharField(source='user.full_name')
    blood_type = serializers.CharField()
    allergies = serializers.CharField()
    chronic_conditions = serializers.CharField()
    last_visit = serializers.SerializerMethodField()
    
    def get_last_visit(self, obj):
        """Get most recent examination"""
        last_exam = Examination.objects.filter(
            patient=obj.user,
            status=Examination.Status.COMPLETED
        ).order_by('-examination_date').first()
        
        if last_exam:
            return {
                'date': last_exam.examination_date,
                'diagnosis': last_exam.final_diagnosis,
                'doctor': last_exam.doctor.full_name
            }
        return None
    
    class Meta:
        fields = [
            'patient_id', 'full_name', 'blood_type', 
            'allergies', 'chronic_conditions', 'last_visit'
        ]
```

**Key Points**:
- Read-only serializer
- Combines PatientProfile + last Examination
- `last_visit` includes nested doctor info
- Used only for STUDENT role

---

### 2. Appointment Serializers

#### 2.1 AppointmentListSerializer
**Purpose**: `GET /appointments` - list view

```python
class AppointmentListSerializer(serializers.ModelSerializer):
    """
    Appointment list view
    Maps to AppointmentSummary schema
    """
    patient = UserSerializer(read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'appointment_date', 
            'status', 'reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
```

**Key Points**:
- Includes nested patient info
- For both student (their own) and doctor/admin (all)

---

#### 2.2 AppointmentCreateSerializer
**Purpose**: `POST /appointments` - create appointment

```python
class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Create new appointment
    Patient automatically set from request.user
    """
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'reason']
    
    def validate_appointment_date(self, value):
        """Ensure appointment is for future date"""
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Appointment date cannot be in the past"
            )
        return value
    
    def validate(self, attrs):
        """Check for existing appointment on same date"""
        user = self.context['request'].user
        appointment_date = attrs['appointment_date']
        
        existing = Appointment.objects.filter(
            patient=user,
            appointment_date=appointment_date,
            status__in=[Appointment.Status.PENDING, Appointment.Status.COMPLETED]
        ).exists()
        
        if existing:
            raise serializers.ValidationError(
                "You already have an appointment on this date"
            )
        
        return attrs
    
    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        validated_data['status'] = Appointment.Status.PENDING
        return super().create(validated_data)
```

**Key Points**:
- Patient auto-set from authenticated user
- Validates no duplicate appointments
- Validates future date
- Status defaults to PENDING

---

#### 2.3 AppointmentDetailSerializer
**Purpose**: `GET /appointments/{id}` - detailed view

```python
class AppointmentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed appointment view with examination if exists
    Maps to AppointmentDetail schema
    """
    patient = UserSerializer(read_only=True)
    examination = serializers.SerializerMethodField()
    cancelled_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'appointment_date', 'status', 
            'reason', 'cancellation_reason', 'cancelled_by',
            'examination', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_examination(self, obj):
        if hasattr(obj, 'examination'):
            return ExaminationSummarySerializer(obj.examination).data
        return None
```

**Key Points**:
- Includes examination if exists
- Shows cancellation info
- Full nested relationships

---

#### 2.4 AppointmentCancelSerializer
**Purpose**: `PATCH /appointments/{id}` - cancel appointment

```python
class AppointmentCancelSerializer(serializers.Serializer):
    """
    Cancel an appointment
    """
    cancellation_reason = serializers.CharField(required=True)
    
    def validate(self, attrs):
        appointment = self.instance
        
        if appointment.status == Appointment.Status.CANCELLED:
            raise serializers.ValidationError(
                "Appointment is already cancelled"
            )
        
        if appointment.status == Appointment.Status.COMPLETED:
            raise serializers.ValidationError(
                "Cannot cancel completed appointment"
            )
        
        return attrs
    
    def update(self, instance, validated_data):
        instance.status = Appointment.Status.CANCELLED
        instance.cancellation_reason = validated_data['cancellation_reason']
        instance.cancelled_by = self.context['request'].user
        instance.save()
        return instance
```

**Key Points**:
- Validates appointment can be cancelled
- Records who cancelled
- Updates status to CANCELLED

---

### 3. Examination Serializers

#### 3.1 ExaminationSummarySerializer
**Purpose**: List view in `/users/me/examinations`

```python
class ExaminationSummarySerializer(serializers.ModelSerializer):
    """
    Summary view for examination lists
    Maps to ExaminationSummary schema
    """
    doctor = UserSerializer(read_only=True)
    patient = UserSerializer(read_only=True)
    
    class Meta:
        model = Examination
        fields = [
            'id', 'patient', 'doctor', 'examination_date',
            'initial_diagnosis', 'final_diagnosis', 'status'
        ]
        read_only_fields = fields
```

**Key Points**:
- Read-only for list views
- Nested doctor and patient info
- Key diagnosis fields only

---

#### 3.2 ExaminationCreateSerializer
**Purpose**: `POST /examinations` - create new examination

```python
class ExaminationCreateSerializer(serializers.ModelSerializer):
    """
    Create new examination record
    Doctor set from request.user
    """
    patient_id = serializers.UUIDField(write_only=True)
    appointment_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    
    class Meta:
        model = Examination
        fields = [
            'patient_id', 'appointment_id', 'symptoms', 
            'initial_diagnosis', 'notes', 'blood_pressure',
            'heart_rate', 'temperature', 'weight', 'height'
        ]
    
    def validate_patient_id(self, value):
        """Ensure patient exists and has STUDENT role"""
        try:
            user = User.objects.get(id=value, role=User.Role.STUDENT)
        except User.DoesNotExist:
            raise serializers.ValidationError("Patient not found")
        return value
    
    def validate_appointment_id(self, value):
        """Validate appointment belongs to patient"""
        if value:
            patient_id = self.initial_data.get('patient_id')
            try:
                appointment = Appointment.objects.get(
                    id=value,
                    patient_id=patient_id,
                    status=Appointment.Status.PENDING
                )
            except Appointment.DoesNotExist:
                raise serializers.ValidationError(
                    "Appointment not found or not valid for this patient"
                )
        return value
    
    def create(self, validated_data):
        patient_id = validated_data.pop('patient_id')
        appointment_id = validated_data.pop('appointment_id', None)
        
        validated_data['patient_id'] = patient_id
        validated_data['doctor'] = self.context['request'].user
        validated_data['status'] = Examination.Status.DRAFT
        
        if appointment_id:
            validated_data['appointment_id'] = appointment_id
        
        return super().create(validated_data)
```

**Key Points**:
- Doctor auto-set from authenticated user
- Validates patient is STUDENT
- Links to appointment if provided
- Status defaults to DRAFT

---

#### 3.3 ExaminationUpdateSerializer
**Purpose**: `PUT /examinations/{id}` - update draft examination

```python
class ExaminationUpdateSerializer(serializers.ModelSerializer):
    """
    Update examination record (only if DRAFT status)
    """
    class Meta:
        model = Examination
        fields = [
            'symptoms', 'initial_diagnosis', 'notes',
            'final_diagnosis', 'prescription',
            'blood_pressure', 'heart_rate', 'temperature',
            'weight', 'height'
        ]
    
    def validate(self, attrs):
        """Ensure examination is still in DRAFT status"""
        if self.instance.status == Examination.Status.COMPLETED:
            raise serializers.ValidationError(
                "Cannot update finalized examination"
            )
        return attrs
```

**Key Points**:
- Only works on DRAFT examinations
- All clinical fields updatable
- Blocks updates to COMPLETED records

---

#### 3.4 ExaminationDetailSerializer
**Purpose**: `GET /examinations/{id}` - detailed view

```python
class ExaminationDetailSerializer(serializers.ModelSerializer):
    """
    Full examination details
    Maps to ExaminationDetail schema
    """
    patient = UserSerializer(read_only=True)
    doctor = UserSerializer(read_only=True)
    appointment = AppointmentListSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    
    class Meta:
        model = Examination
        fields = [
            'id', 'patient', 'doctor', 'appointment',
            'symptoms', 'initial_diagnosis', 'notes',
            'final_diagnosis', 'prescription',
            'blood_pressure', 'heart_rate', 'temperature',
            'weight', 'height', 'status', 'examination_date',
            'finalized_at', 'attachments', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_attachments(self, obj):
        """Get uploaded files for this examination"""
        return UploadedFileSerializer(
            obj.attachments.all(), 
            many=True
        ).data
```

**Key Points**:
- Complete examination record
- Nested patient, doctor, appointment
- Includes attachments
- All fields read-only in detail view

---

#### 3.5 ExaminationFinalizeSerializer
**Purpose**: `POST /examinations/{id}/finalize` - finalize examination

```python
class ExaminationFinalizeSerializer(serializers.Serializer):
    """
    Finalize examination (make immutable)
    """
    def validate(self, attrs):
        examination = self.instance
        
        if examination.status == Examination.Status.COMPLETED:
            raise serializers.ValidationError(
                "Examination is already finalized"
            )
        
        if not examination.final_diagnosis:
            raise serializers.ValidationError(
                "Final diagnosis is required to finalize"
            )
        
        if not examination.prescription:
            raise serializers.ValidationError(
                "Prescription is required to finalize"
            )
        
        return attrs
    
    def update(self, instance, validated_data):
        instance.status = Examination.Status.COMPLETED
        instance.finalized_at = timezone.now()
        instance.save()
        
        # Update related appointment status
        if instance.appointment:
            instance.appointment.status = Appointment.Status.COMPLETED
            instance.appointment.save()
        
        return instance
```

**Key Points**:
- Validates required fields present
- Sets status to COMPLETED
- Records finalization timestamp
- Updates related appointment
- Triggers audit log (in view)

---

### 4. Patient Lookup Serializers

#### 4.1 PatientLookupSerializer
**Purpose**: `GET /patients/lookup?qr_code={uuid}` - QR code scan

```python
class PatientLookupSerializer(serializers.ModelSerializer):
    """
    Patient information from QR code scan
    Maps to PatientLookup schema
    """
    patient_profile = PatientProfileSerializer(read_only=True)
    last_diagnosis = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'student_id', 'phone_number',
            'email', 'patient_profile', 'last_diagnosis'
        ]
        read_only_fields = fields
    
    def get_last_diagnosis(self, obj):
        """Get most recent completed examination"""
        last_exam = Examination.objects.filter(
            patient=obj,
            status=Examination.Status.COMPLETED
        ).select_related('doctor').order_by('-examination_date').first()
        
        if last_exam:
            return {
                'date': last_exam.examination_date,
                'diagnosis': last_exam.final_diagnosis,
                'prescription': last_exam.prescription,
                'doctor': last_exam.doctor.full_name
            }
        return None
```

**Key Points**:
- Only for doctors/admins
- Includes patient profile
- Shows last completed examination
- Used for QR code workflow

---

#### 4.2 PatientExaminationHistorySerializer
**Purpose**: `GET /patients/{id}/examinations` - patient history

```python
class PatientExaminationHistorySerializer(serializers.ModelSerializer):
    """
    Patient examination history for doctors
    Full access to all past examinations
    """
    doctor = UserSerializer(read_only=True)
    
    class Meta:
        model = Examination
        fields = [
            'id', 'doctor', 'examination_date', 'symptoms',
            'initial_diagnosis', 'final_diagnosis', 'prescription',
            'blood_pressure', 'heart_rate', 'temperature',
            'weight', 'height', 'status', 'finalized_at'
        ]
        read_only_fields = fields
```

**Key Points**:
- Read-only history view
- Only accessible by doctors/admins
- Full examination details
- Ordered by date (most recent first)

---

### 5. Ticket Serializers

#### 5.1 TicketListSerializer
**Purpose**: `GET /tickets` - list tickets

```python
class TicketListSerializer(serializers.ModelSerializer):
    """
    Ticket summary for list view
    Maps to TicketSummary schema
    """
    creator = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    reply_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'creator', 'assigned_to', 'subject',
            'status', 'created_at', 'last_reply_at',
            'reply_count'
        ]
        read_only_fields = fields
    
    def get_reply_count(self, obj):
        return obj.replies.count()
```

**Key Points**:
- Shows reply count
- Nested creator and assignee
- For both students and doctors (filtered by role)

---

#### 5.2 TicketCreateSerializer
**Purpose**: `POST /tickets` - create ticket

```python
class TicketCreateSerializer(serializers.ModelSerializer):
    """
    Create new support ticket
    Creator auto-set from request.user (must be STUDENT)
    """
    related_appointment_id = serializers.UUIDField(
        required=False, 
        allow_null=True, 
        write_only=True
    )
    
    class Meta:
        model = Ticket
        fields = ['subject', 'related_appointment_id']
    
    def validate_related_appointment_id(self, value):
        """Ensure appointment belongs to creator"""
        if value:
            user = self.context['request'].user
            try:
                Appointment.objects.get(id=value, patient=user)
            except Appointment.DoesNotExist:
                raise serializers.ValidationError(
                    "Appointment not found or does not belong to you"
                )
        return value
    
    def create(self, validated_data):
        related_appointment_id = validated_data.pop('related_appointment_id', None)
        
        validated_data['creator'] = self.context['request'].user
        validated_data['status'] = Ticket.Status.OPEN
        
        if related_appointment_id:
            validated_data['related_appointment_id'] = related_appointment_id
        
        return super().create(validated_data)
```

**Key Points**:
- Creator auto-set (STUDENT only)
- Optional appointment link
- Status defaults to OPEN

---

#### 5.3 TicketDetailSerializer
**Purpose**: `GET /tickets/{id}` - ticket with replies

```python
class TicketDetailSerializer(serializers.ModelSerializer):
    """
    Full ticket details with conversation thread
    Maps to TicketDetail schema
    """
    creator = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    related_appointment = AppointmentListSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'creator', 'assigned_to', 'subject',
            'status', 'related_appointment', 'replies',
            'created_at', 'updated_at', 'resolved_at',
            'last_reply_at'
        ]
        read_only_fields = fields
    
    def get_replies(self, obj):
        return TicketReplySerializer(
            obj.replies.all().select_related('author'),
            many=True
        ).data
```

**Key Points**:
- Includes full conversation thread
- Nested appointment if linked
- Ordered replies (oldest first)

---

#### 5.4 TicketReplySerializer
**Purpose**: View ticket replies

```python
class TicketReplySerializer(serializers.ModelSerializer):
    """
    Ticket reply/message display
    """
    author = UserSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketReply
        fields = [
            'id', 'author', 'content', 'is_staff_reply',
            'attachments', 'created_at'
        ]
        read_only_fields = fields
    
    def get_attachments(self, obj):
        return UploadedFileSerializer(
            obj.attachments.all(),
            many=True
        ).data
```

**Key Points**:
- Read-only in detail view
- Shows author info
- Includes attachments

---

#### 5.5 TicketReplyCreateSerializer
**Purpose**: `POST /tickets/{id}/replies` - add reply

```python
class TicketReplyCreateSerializer(serializers.ModelSerializer):
    """
    Create reply to ticket
    """
    attachment_url = serializers.URLField(required=False, allow_blank=True)
    
    class Meta:
        model = TicketReply
        fields = ['content', 'attachment_url']
    
    def validate(self, attrs):
        ticket = self.context['ticket']
        
        if ticket.status == Ticket.Status.RESOLVED:
            raise serializers.ValidationError(
                "Cannot reply to resolved ticket"
            )
        
        return attrs
    
    def create(self, validated_data):
        user = self.context['request'].user
        ticket = self.context['ticket']
        
        validated_data['ticket'] = ticket
        validated_data['author'] = user
        validated_data['is_staff_reply'] = user.role in [
            User.Role.DOCTOR, 
            User.Role.ADMIN
        ]
        
        reply = super().create(validated_data)
        
        # Update ticket's last_reply_at
        ticket.last_reply_at = timezone.now()
        
        # Update status to PENDING if staff replied
        if reply.is_staff_reply and ticket.status == Ticket.Status.OPEN:
            ticket.status = Ticket.Status.PENDING
        
        ticket.save()
        
        return reply
```

**Key Points**:
- Author auto-set
- `is_staff_reply` based on role
- Updates ticket's `last_reply_at`
- Changes status to PENDING on staff reply

---

#### 5.6 TicketCloseSerializer
**Purpose**: `POST /tickets/{id}/close` - close ticket

```python
class TicketCloseSerializer(serializers.Serializer):
    """
    Close/resolve a ticket
    """
    def validate(self, attrs):
        ticket = self.instance
        
        if ticket.status == Ticket.Status.RESOLVED:
            raise serializers.ValidationError(
                "Ticket is already resolved"
            )
        
        return attrs
    
    def update(self, instance, validated_data):
        instance.status = Ticket.Status.RESOLVED
        instance.resolved_at = timezone.now()
        instance.save()
        return instance
```

**Key Points**:
- Sets status to RESOLVED
- Records resolution timestamp
- Available to creator and assigned staff

---

### 6. File Upload Serializers

#### 6.1 ImageUploadSerializer
**Purpose**: `POST /upload/image` - upload image

```python
class ImageUploadSerializer(serializers.ModelSerializer):
    """
    Upload image file
    """
    file = serializers.ImageField(required=True)
    
    class Meta:
        model = UploadedFile
        fields = ['file']
    
    def validate_file(self, value):
        """Validate file size and type"""
        # Check file size (10MB max)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size cannot exceed 10MB"
            )
        
        # Check MIME type
        valid_types = ['image/jpeg', 'image/png']
        if value.content_type not in valid_types:
            raise serializers.ValidationError(
                "Only JPEG and PNG images are allowed"
            )
        
        return value
    
    def create(self, validated_data):
        file = validated_data['file']
        user = self.context['request'].user
        
        uploaded_file = UploadedFile.objects.create(
            uploaded_by=user,
            file=file,
            file_name=file.name,
            file_size=file.size,
            mime_type=file.content_type,
            url=f"{settings.MEDIA_URL}{file.name}"  # Will be updated after save
        )
        
        # Update URL after save (when path is known)
        uploaded_file.url = self.context['request'].build_absolute_uri(
            uploaded_file.file.url
        )
        uploaded_file.save()
        
        return uploaded_file
```

**Key Points**:
- Validates image type and size
- Auto-generates URL
- Tracks uploader

---

#### 6.2 UploadedFileSerializer
**Purpose**: Display uploaded file info

```python
class UploadedFileSerializer(serializers.ModelSerializer):
    """
    Uploaded file representation
    Maps to ImageUploadResponse schema
    """
    class Meta:
        model = UploadedFile
        fields = ['id', 'url', 'file_name', 'file_size', 'mime_type', 'created_at']
        read_only_fields = fields
```

**Key Points**:
- Read-only representation
- Used in examination and ticket attachments

---

### 7. Authentication Serializers

#### 7.1 LoginSerializer
**Purpose**: `POST /auth/login` - user authentication

```python
class LoginSerializer(serializers.Serializer):
    """
    Login with username and password
    Returns JWT tokens
    """
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError(
                "Invalid username or password"
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                "User account is disabled"
            )
        
        attrs['user'] = user
        return attrs
```

**Key Points**:
- Returns JWT tokens (handled in view)
- Validates credentials
- Checks account status

---

#### 7.2 TokenSerializer
**Purpose**: JWT token response

```python
class TokenSerializer(serializers.Serializer):
    """
    JWT token pair response
    Maps to LoginResponse schema
    """
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default='Bearer')
    expires_in = serializers.IntegerField()
    user = CurrentUserSerializer()
```

**Key Points**:
- Includes user profile
- Token metadata
- Standard JWT response format

---

## Serializer Organization

### File Structure
```
mainAPI/
    serializers/
        __init__.py
        user.py          # User, PatientProfile, DoctorProfile serializers
        auth.py          # Login, Token serializers
        appointment.py   # Appointment serializers
        examination.py   # Examination serializers
        patient.py       # Patient lookup serializers
        ticket.py        # Ticket and TicketReply serializers
        upload.py        # File upload serializers
```

### Import Pattern
```python
# mainAPI/serializers/__init__.py
from .user import (
    UserSerializer,
    CurrentUserSerializer,
    PatientProfileSerializer,
    DoctorProfileSerializer,
    MedicalSummarySerializer
)
from .auth import LoginSerializer, TokenSerializer
from .appointment import (
    AppointmentListSerializer,
    AppointmentCreateSerializer,
    AppointmentDetailSerializer,
    AppointmentCancelSerializer
)
# ... etc
```

---

## Validation Strategies

### 1. Field-Level Validation
```python
def validate_<field_name>(self, value):
    """Validate individual field"""
    # Custom validation logic
    return value
```

**Usage**: Date validation, format checks, range validation

---

### 2. Object-Level Validation
```python
def validate(self, attrs):
    """Validate multiple fields together"""
    # Cross-field validation
    return attrs
```

**Usage**: Business logic, constraint checks, relationship validation

---

### 3. Model Constraints
```python
class Meta:
    validators = [
        UniqueTogetherValidator(
            queryset=Model.objects.all(),
            fields=['field1', 'field2']
        )
    ]
```

**Usage**: Database-level constraints in serializer

---

## Performance Optimization

### 1. Select Related
```python
class ExaminationDetailSerializer(serializers.ModelSerializer):
    # In ViewSet:
    queryset = Examination.objects.select_related(
        'patient', 'doctor', 'appointment'
    ).prefetch_related('attachments')
```

**Purpose**: Reduce N+1 queries for foreign keys

---

### 2. Prefetch Related
```python
class TicketDetailSerializer(serializers.ModelSerializer):
    # In ViewSet:
    queryset = Ticket.objects.prefetch_related(
        'replies__author',
        'replies__attachments'
    )
```

**Purpose**: Optimize many-to-many and reverse foreign key lookups

---

### 3. Serializer Context
```python
serializer = ExaminationDetailSerializer(
    examination,
    context={
        'request': request,
        'view': self,
        'format': format
    }
)
```

**Purpose**: Pass request data, avoid redundant queries

---

## Permission Integration

### Serializer-Level Permissions
```python
class ExaminationDetailSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        """Hide sensitive fields based on user role"""
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and request.user.role == User.Role.STUDENT:
            # Students can't see internal notes
            data.pop('notes', None)
        
        return data
```

**Purpose**: Field-level visibility control

---

## Error Response Format

### Standard Error Structure
```python
{
    "error": "Invalid input",
    "details": {
        "field_name": ["Error message 1", "Error message 2"]
    },
    "status_code": 400
}
```

**Handled by**: DRF exception handler (customize in settings)

---

## API Schema Mapping

| API Schema (api.yaml) | Serializer |
|----------------------|------------|
| `UserProfile` | `CurrentUserSerializer` |
| `MedicalSummary` | `MedicalSummarySerializer` |
| `AppointmentSummary` | `AppointmentListSerializer` |
| `AppointmentDetail` | `AppointmentDetailSerializer` |
| `ExaminationSummary` | `ExaminationSummarySerializer` |
| `ExaminationDetail` | `ExaminationDetailSerializer` |
| `PatientLookup` | `PatientLookupSerializer` |
| `TicketSummary` | `TicketListSerializer` |
| `TicketDetail` | `TicketDetailSerializer` |
| `TicketReply` | `TicketReplySerializer` |
| `ImageUploadResponse` | `UploadedFileSerializer` |
| `LoginResponse` | `TokenSerializer` |

---

## Testing Strategy

### 1. Serializer Unit Tests
```python
class AppointmentSerializerTestCase(TestCase):
    def test_create_appointment_validation(self):
        """Test appointment creation validates date"""
        # Test logic
    
    def test_duplicate_appointment_prevented(self):
        """Test unique constraint enforcement"""
        # Test logic
```

---

### 2. Integration Tests
```python
class AppointmentAPITestCase(APITestCase):
    def test_create_appointment_endpoint(self):
        """Test full create flow with serializer"""
        # Test logic
```

---

## Next Steps

1. **Create serializer files** in `mainAPI/serializers/` directory
2. **Implement base serializers** (User, Auth)
3. **Add validation methods** for business rules
4. **Optimize queries** with select_related/prefetch_related
5. **Write serializer tests** for each serializer
6. **Integrate with ViewSets** (next phase)
7. **Document API responses** with drf-spectacular
8. **Add custom exception handlers** for consistent error format

---

## Dependencies

```python
# requirements.txt additions for serializers
djangorestframework>=3.14.0
djangorestframework-simplejwt>=5.3.0
Pillow>=10.0.0  # For ImageField
drf-spectacular>=0.26.0  # For OpenAPI docs
```

---

*Generated: 2025-12-26*
*Based on: Model Plan (model.md) and API Specification v1.0.0 (api.yaml)*
