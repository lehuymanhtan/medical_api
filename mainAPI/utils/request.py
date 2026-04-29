from django.conf import settings


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    remote_addr = request.META.get('REMOTE_ADDR')
    trusted_proxies = getattr(settings, 'TRUSTED_PROXY_IPS', [])

    if x_forwarded_for and remote_addr in trusted_proxies:
        return x_forwarded_for.split(',')[0].strip()
    return remote_addr
