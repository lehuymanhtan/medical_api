#!/bin/bash
set -e

echo "Checking and applying database migrations..."
python manage.py migrate --noinput

echo "Starting Supervisor..."
exec "$@"
