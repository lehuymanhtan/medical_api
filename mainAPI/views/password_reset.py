"""
Password Reset Views
Provides two public endpoints:
  POST /auth/forgot-password  – request a reset token (sent by email via Resend)
  POST /auth/reset-password   – consume the token and set a new password
"""
import secrets
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiExample

from mainAPI.models import User, PasswordResetToken
from mainAPI.utils.email import send_password_reset_email

logger = logging.getLogger(__name__)


class ForgotPasswordView(APIView):
    """
    Request a password reset token.
    A one-time token is generated and emailed to the user.
    Always returns 200 to prevent user enumeration.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        operation_id='forgotPassword',
        summary='Yêu cầu đặt lại mật khẩu',
        description=(
            'Tạo mã OTP 8 chữ số và gửi qua email. '
            'Luôn trả về 200 để tránh lộ thông tin tài khoản tồn tại hay không.'
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {
                        'type': 'string',
                        'format': 'email',
                        'description': 'Địa chỉ email của tài khoản cần đặt lại mật khẩu'
                    }
                },
                'required': ['email']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            },
            400: {'description': 'Thiếu trường email'},
        },
        examples=[
            OpenApiExample(
                'Forgot Password Request',
                value={'email': 'user@example.com'},
                request_only=True,
            ),
            OpenApiExample(
                'Forgot Password Response',
                value={'message': 'Nếu email tồn tại, một liên kết đặt lại mật khẩu đã được gửi.'},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        email = request.data.get('email', '').strip().lower()

        if not email:
            return Response(
                {'error': 'Email là bắt buộc'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Always return the same success response to prevent user enumeration
        generic_response = Response(
            {'message': 'Nếu email tồn tại, một mã đặt lại mật khẩu đã được gửi đến email của bạn.'},
            status=status.HTTP_200_OK
        )

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            logger.info("Password reset requested for non-existent email: %s", email)
            return generic_response

        # Invalidate any existing unused tokens for this user
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate a cryptographically secure 8-digit numeric code
        raw_token = f"{secrets.randbelow(100_000_000):08d}"

        PasswordResetToken.objects.create(user=user, token=raw_token)

        # Send the email
        email_sent = send_password_reset_email(
            recipient_email=user.email,
            recipient_name=user.full_name,
            reset_token=raw_token,
        )

        if not email_sent:
            logger.error("Could not dispatch reset email for user %s", user.id)

        return generic_response


class ResetPasswordView(APIView):
    """
    Consume a reset token and set a new password.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        operation_id='resetPassword',
        summary='Đặt lại mật khẩu bằng token',
        description='Xác thực mã OTP 8 chữ số và cập nhật mật khẩu mới cho người dùng.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {
                        'type': 'string',
                        'format': 'email',
                        'description': 'Địa chỉ email của tài khoản'
                    },
                    'token': {
                        'type': 'string',
                        'description': 'Mã OTP 8 chữ số nhận được qua email'
                    },
                    'new_password': {
                        'type': 'string',
                        'description': 'Mật khẩu mới (tối thiểu 8 ký tự)'
                    }
                },
                'required': ['email', 'token', 'new_password']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            },
            400: {'description': 'Token không hợp lệ, đã hết hạn, hoặc mật khẩu không đủ mạnh'},
        },
        examples=[
            OpenApiExample(
                'Reset Password Request',
                value={
                    'email': 'user@example.com',
                    'token': '12345678',
                    'new_password': 'MyNewSecureP@ss1'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Reset Password Response',
                value={'message': 'Đặt lại mật khẩu thành công.'},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        token_str = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')

        if not email or not token_str or not new_password:
            return Response(
                {'error': 'Email, token và mật khẩu mới là bắt buộc'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Look up the token and verify it matches the provided email
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(
                token=token_str,
                user__email__iexact=email
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Token không hợp lệ hoặc đã hết hạn'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reset_token.is_valid():
            return Response(
                {'error': 'Token không hợp lệ hoặc đã hết hạn'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = reset_token.user

        # Validate the new password against Django's validators
        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response(
                {'error': exc.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark token as used and update the password atomically
        reset_token.is_used = True
        reset_token.save(update_fields=['is_used'])

        user.set_password(new_password)
        user.save(update_fields=['password'])

        logger.info("Password reset successful for user %s", user.id)

        return Response(
            {'message': 'Đặt lại mật khẩu thành công.'},
            status=status.HTTP_200_OK
        )
