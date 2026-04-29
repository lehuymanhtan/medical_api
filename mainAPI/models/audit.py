import uuid
from django.db import models
from .user import User


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
        APPOINTMENT_UPDATED = 'APPOINTMENT_UPDATED', 'Appointment Updated'
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
        USER_CHANGE_PASSWORD = 'USER_CHANGE_PASSWORD', 'User Change Password'

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
