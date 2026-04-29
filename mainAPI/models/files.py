import uuid
from django.db import models
from .user import User
from .examination import Examination
from .ticket import TicketReply


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
