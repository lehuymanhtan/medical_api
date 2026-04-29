import uuid
from django.db import models
from django.utils import timezone
from .user import User


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
