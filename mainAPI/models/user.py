import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser
    Supports RBAC with three roles: Student, Doctor, Admin
    """
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        DOCTOR = 'DOCTOR', 'Doctor'
        ADMIN = 'ADMIN', 'Admin'

    class Sex(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices)
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    cohort = models.CharField(max_length=50, blank=True)
    class_name = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=10, choices=Sex.choices, blank=True)
    address = models.TextField(blank=True)

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
    allergies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allergies"
    )
    chronic_conditions = models.TextField(blank=True)

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
