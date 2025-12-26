"""
Celery tasks for mainAPI
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from mainAPI.models import Ticket


@shared_task
def auto_close_inactive_tickets():
    """
    Auto-close tickets with no reply within the configured threshold (15 minutes)
    Runs periodically via Celery Beat
    """
    threshold = timezone.now() - timedelta(minutes=Ticket.AUTO_CLOSE_THRESHOLD_MINUTES)
    
    # Find tickets that haven't been replied to in 15+ minutes
    tickets = Ticket.objects.filter(
        status__in=['OPEN', 'IN_PROGRESS'],
        last_reply_at__lt=threshold
    )
    
    count = 0
    for ticket in tickets:
        ticket.close()
        count += 1
    
    return f"Auto-closed {count} tickets"
