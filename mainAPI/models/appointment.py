import uuid
from django.db import models
from .user import User


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
        limit_choices_to={'role': User.Role.STUDENT}
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
