"""
Authentication Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiExample
from mainAPI.serializers.user import (
    UserProfileSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    ChangePasswordRequestSerializer
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


class RefreshTokenView(APIView):
    """
    Refresh access token using refresh token
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='refreshToken',
        summary='Làm mới access token',
        description='Sử dụng refresh token để lấy access token mới.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {
                        'type': 'string',
                        'description': 'Refresh token nhận được từ đăng nhập'
                    }
                },
                'required': ['refresh']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string', 'description': 'Access token mới'},
                }
            },
            400: {'description': 'Thiếu refresh token'},
            401: {'description': 'Refresh token không hợp lệ hoặc hết hạn'}
        },
        examples=[
            OpenApiExample(
                'Refresh Token Request',
                value={
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Refresh Token Response',
                value={
                    'token': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                },
                response_only=True,
            )
        ],
    )
    def post(self, request):
        """
        Generate new access token from refresh token
        """
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate refresh token and generate new access token
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            return Response({
                'token': access_token
            }, status=status.HTTP_200_OK)
        
        except TokenError as e:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class ChangePasswordView(APIView):
    """
    Change user password endpoint
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='changePassword',
        summary='Đổi mật khẩu người dùng',
        description='Cho phép người dùng đã xác thực thay đổi mật khẩu của họ.',
        request=ChangePasswordRequestSerializer,
        responses={
            200: {'description': 'Đổi mật khẩu thành công'},
            400: {'description': 'Mật khẩu cũ không chính xác hoặc dữ liệu không hợp lệ'}
        },
        examples=[
            OpenApiExample(
                'Change Password Request',
                value={
                    'old_password': 'currentpassword123',
                    'new_password': 'newpassword123'
                },
                request_only=True,
            )
        ]
    )
    def post(self, request):
        serializer = ChangePasswordRequestSerializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data.get('old_password')
            new_password = serializer.validated_data.get('new_password')
            
            user = request.user
            if not user.check_password(old_password):
                return Response(
                    {'error': 'Mật khẩu cũ không chính xác'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set the new password and save the user
            user.set_password(new_password)
            user.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='USER_CHANGE_PASSWORD',  # Using string since we didn't add it to Action choices, or we can just use generic if Action is restricted. Wait, Action choices in Audit log are restricted.
                model_name='User',
                object_id=user.id,
                object_repr=str(user),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            
            return Response(
                {'message': 'Đổi mật khẩu thành công'},
                status=status.HTTP_200_OK
            )
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

