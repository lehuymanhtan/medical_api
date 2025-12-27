"""
Authentication Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiExample
from mainAPI.serializers.user import (
    UserProfileSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer
)
from mainAPI.models import AuditLog


class LoginView(APIView):
    """
    Public login endpoint
    Returns JWT tokens and user profile
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='login',
        summary='Đăng nhập vào hệ thống',
        description='Xác thực người dùng và trả về JWT token cùng thông tin hồ sơ.',
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer},
        examples=[
            OpenApiExample(
                'Login Example',
                value={
                    'username': 'student001',
                    'password': 'password123'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Login Response',
                value={
                    'token': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    'user': {
                        'id': '123e4567-e89b-12d3-a456-426614174000',
                        'full_name': 'Nguyễn Văn A',
                        'role': 'STUDENT',
                        'student_id': 'SV001'
                    }
                },
                response_only=True,
            )
        ],
    )
    def post(self, request):
        """
        Authenticate user and return JWT tokens
        """
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is inactive'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Create audit log
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.USER_LOGIN,
            model_name='User',
            object_id=user.id,
            object_repr=str(user),
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Serialize user data
        user_serializer = UserProfileSerializer(user)
        
        return Response({
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_serializer.data
        }, status=status.HTTP_200_OK)
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
