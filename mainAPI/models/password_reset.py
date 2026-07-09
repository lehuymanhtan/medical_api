import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta

from .user import User


def default_expires_at():
    """Token expires after 15 minutes."""
    return timezone.now() + timedelta(minutes=15)


class PasswordResetToken(models.Model):
    """
    One-time password reset token.
    Generated on forgot-password request, consumed on reset-password.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=8, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expires_at)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        """Return True if the token has not been used and has not expired."""
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"PasswordResetToken for {self.user.email} (used={self.is_used})"
