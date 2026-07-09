#!/bin/bash
set -e

# Optional: Create a swap file to help with 512MB RAM limits
if [ "$ENABLE_SWAP" = "true" ]; then
    echo "Attempting to create and enable 512MB swap..."
    set +e # Disable exit-on-error in case swapon is denied by the host
    fallocate -l 512M /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=512 status=none
    chmod 0600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if [ $? -eq 0 ]; then
        echo "Swap enabled successfully."
    else
        echo "WARNING: Failed to enable swap. Your hosting provider might block this (requires CAP_SYS_ADMIN)."
    fi
    set -e # Re-enable exit-on-error
fi

echo "Checking and applying database migrations..."
python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Checking/creating superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password, full_name='Super Admin', role='ADMIN')
    print('Superuser created successfully.')
else:
    print('Superuser already exists.')
"
fi

echo "Starting Supervisor..."
exec "$@"
