import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .user import User


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
