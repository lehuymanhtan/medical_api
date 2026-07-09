import uuid
from django.db import models
from django.utils import timezone
from .user import User


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
        limit_choices_to={'role': User.Role.STUDENT}
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
