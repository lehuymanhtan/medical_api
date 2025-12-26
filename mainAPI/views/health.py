"""
Health check and utility views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import connection
from django.core.cache import cache
import redis


class HealthCheckView(APIView):
    """
    Public health check endpoint for monitoring
    Checks database and Redis connectivity
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Returns health status of the application
        """
        health_status = {
            'status': 'healthy',
            'database': 'unknown',
            'redis': 'unknown',
        }
        
        # Check database connectivity
        try:
            connection.ensure_connection()
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Check Redis connectivity
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                health_status['redis'] = 'connected'
            else:
                health_status['redis'] = 'error'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['redis'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Return appropriate status code
        if health_status['status'] == 'healthy':
            return Response(health_status, status=status.HTTP_200_OK)
        else:
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)
