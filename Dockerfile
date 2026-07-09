# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies, Redis, and Supervisor
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libmagic1 \
        redis-server \
        supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project
COPY . /app/

# Create directories for logs, media, and supervisor
RUN mkdir -p logs media /var/log/supervisor

# Collect static files
RUN DEVELOPMENT=True python manage.py collectstatic --noinput

# Create a non-root user and change ownership
RUN useradd -m django && chown -R django:django /app

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy and set up the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Default port, can be overridden by docker run -e PORT=...
ENV PORT=8000
EXPOSE $PORT

# Set entrypoint to run migrations, then start supervisor
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
