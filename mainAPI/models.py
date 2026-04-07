import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser
    Supports RBAC with three roles: Student, Doctor, Admin
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
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['student_id']),
            models.Index(fields=['role', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.role})"


class PatientProfile(models.Model):
    """
    Extended medical profile for users with STUDENT role
    One-to-One relationship with User model
    """
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='patient_profile',
        limit_choices_to={'role': 'STUDENT'}
    )
    
    blood_type = models.CharField(
        max_length=5, 
        choices=BLOOD_TYPE_CHOICES, 
        blank=True
    )
    allergies = models.TextField(
        blank=True, 
        help_text="Comma-separated list of allergies"
    )
    chronic_conditions = models.TextField(blank=True)
    
    date_of_birth = models.DateField(null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    fasting_blood_sugar = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hba1c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    red_blood_cells = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hemoglobin = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hematocrit = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    white_blood_cells = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    platelets = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    creatinine = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_urea_nitrogen = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ast_sgot = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    alt_sgpt = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_bilirubin = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_cholesterol = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ldl_cholesterol = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hdl_cholesterol = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    triglycerides = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sodium = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    potassium = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    calcium = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Patient Profile: {self.user.full_name}"


class DoctorProfile(models.Model):
    """
    Extended profile for users with DOCTOR or ADMIN role
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='doctor_profile',
        limit_choices_to={'role__in': ['DOCTOR', 'ADMIN']}
    )
    
    specialization = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Dr. {self.user.full_name} - {self.specialization}"


class Appointment(models.Model):
    """
    Appointment booking - date-only registration for medical visits
    Doctor assigned later when creating examination
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='appointments',
        limit_choices_to={'role': 'STUDENT'}
    )
    
    appointment_date = models.DateField()
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    reason = models.TextField()
    
    # Cancellation tracking
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='cancelled_appointments'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-appointment_date']
        indexes = [
            models.Index(fields=['appointment_date', 'status']),
            models.Index(fields=['patient', 'appointment_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['patient', 'appointment_date'],
                name='one_appointment_per_patient_per_day'
            )
        ]
    
    def __str__(self):
        return f"Appointment: {self.patient.full_name} on {self.appointment_date}"


class Examination(models.Model):
    """
    Medical examination record (core clinical data)
    Immutable once finalized (COMPLETED status)
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        COMPLETED = 'COMPLETED', 'Completed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='examinations_as_patient',
        limit_choices_to={'role': 'STUDENT'}
    )
    doctor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='examinations_as_doctor',
        limit_choices_to={'role__in': ['DOCTOR', 'ADMIN']}
    )
    appointment = models.OneToOneField(
        'Appointment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='examination'
    )
    
    # Examination data
    symptoms = models.TextField(blank=True)
    initial_diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Final diagnosis (locked after finalize)
    final_diagnosis = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    
    # Vital signs
    blood_pressure = models.CharField(max_length=20, blank=True)
    heart_rate = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(300)]
    )
    temperature = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(30.0), MaxValueValidator(45.0)]
    )
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT
    )
    
    examination_date = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-examination_date']
        indexes = [
            models.Index(fields=['status', 'examination_date']),
            models.Index(fields=['patient', '-examination_date']),
        ]
    
    def __str__(self):
        return f"Examination: {self.patient.full_name} by Dr. {self.doctor.full_name} ({self.status})"
    
    def finalize(self):
        """Mark examination as completed and lock it"""
        if self.status == self.Status.COMPLETED:
            raise ValueError("Examination is already finalized")
        
        self.status = self.Status.COMPLETED
        self.finalized_at = timezone.now()
        self.save()


class Ticket(models.Model):
    """
    Support ticket system for students to communicate with doctors
    Auto-closes if no reply within 15 minutes
    """
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
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
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.OPEN
    )
    
    # Optional link to appointment
    related_appointment = models.ForeignKey(
        'Appointment', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    last_reply_at = models.DateTimeField(null=True, blank=True)
    
    # Auto-close configuration
    AUTO_CLOSE_THRESHOLD_MINUTES = 15
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['creator', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.id}: {self.subject} ({self.status})"
    
    def close(self):
        """Close/resolve the ticket"""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save()


class TicketReply(models.Model):
    """
    Reply/message in a ticket conversation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='replies'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='ticket_replies'
    )
    
    content = models.TextField()
    is_staff_reply = models.BooleanField(default=False)
    
    # Attachments
    attachment_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Ticket replies'
    
    def __str__(self):
        return f"Reply by {self.author.full_name} on Ticket #{self.ticket.id}"
    
    def save(self, *args, **kwargs):
        # Auto-set is_staff_reply based on author's role
        if self.author.role in [User.Role.DOCTOR, User.Role.ADMIN]:
            self.is_staff_reply = True
        
        # Update ticket's last_reply_at
        self.ticket.last_reply_at = timezone.now()
        self.ticket.save(update_fields=['last_reply_at'])
        
        super().save(*args, **kwargs)


class UploadedFile(models.Model):
    """
    Track uploaded image files only (.jpg, .jpeg, .png)
    Can be associated with examinations or ticket replies
    """
    MIME_TYPE_CHOICES = [
        ('image/jpeg', 'JPEG'),
        ('image/png', 'PNG'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='uploaded_files'
    )
    
    file = models.ImageField(upload_to='uploads/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100, choices=MIME_TYPE_CHOICES)
    
    url = models.URLField()
    
    # Optional associations
    examination = models.ForeignKey(
        Examination, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attachments'
    )
    ticket_reply = models.ForeignKey(
        TicketReply,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attachments'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"File: {self.file_name} (uploaded by {self.uploaded_by.full_name})"


class AuditLog(models.Model):
    """
    Comprehensive audit trail for sensitive operations
    Tracks all critical actions in the system
    Append-only log - cannot be deleted or modified
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
        
        # Patient data access
        PATIENT_QR_SCANNED = 'PATIENT_QR_SCANNED', 'Patient QR Code Scanned'
        PATIENT_HISTORY_VIEWED = 'PATIENT_HISTORY_VIEWED', 'Patient History Viewed'
        PATIENT_RECORD_ACCESSED = 'PATIENT_RECORD_ACCESSED', 'Patient Record Accessed'
        
        # User actions
        USER_LOGIN = 'USER_LOGIN', 'User Login'
        USER_LOGOUT = 'USER_LOGOUT', 'User Logout'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='audit_logs'
    )
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
    
    def __str__(self):
        return f"{self.action} by {self.user.full_name if self.user else 'Unknown'} at {self.timestamp}"


class FCMDeviceToken(models.Model):
    """
    Stores Firebase Cloud Messaging device tokens for users
    to send push notifications.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='fcm_tokens'
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['token']),
        ]

    def __str__(self):
        return f"Token for {self.user.full_name}"


class QueueEntry(models.Model):
    """
    Daily queue management. Resets each day.
    """
    class Status(models.TextChoices):
        WAITING = 'WAITING', 'Waiting'
        CALLED = 'CALLED', 'Called'
        CANCELLED = 'CANCELLED', 'Cancelled'
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='queue_entries',
        limit_choices_to={'role': 'STUDENT'}
    )
    date = models.DateField(default=timezone.now)
    number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.WAITING
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'number']
        unique_together = ['date', 'number']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['patient', 'date']),
        ]

    def __str__(self):
        return f"Queue #{self.number} - {self.patient.full_name} ({self.date})"

