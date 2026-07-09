"""
Admin Account Management Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiExample
from mainAPI.serializers.user import (
    CreateAccountSerializer,
    BatchCreateAccountSerializer,
    UserProfileSerializer,
)
from mainAPI.permissions import IsAdmin


class AdminCreateAccountView(APIView):
    """
    Admin-only endpoint to create a new user account.
    """
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Admin'],
        operation_id='adminCreateAccount',
        summary='Tạo tài khoản người dùng mới (Admin)',
        description=(
            'Chỉ Admin mới có thể tạo tài khoản. '
            'Yêu cầu: username, name, cohort, class_name, password. '
            'Nếu không truyền email, hệ thống sẽ để trống email. '
            'Tài khoản sinh viên sẽ được tự động khởi tạo PatientProfile.'
        ),
        request=CreateAccountSerializer,
        responses={
            201: UserProfileSerializer,
            400: {'description': 'Dữ liệu không hợp lệ'},
            403: {'description': 'Không có quyền truy cập'},
        },
        examples=[
            OpenApiExample(
                'Create Student Account',
                value={
                    'username': 'sv2024001',
                    'name': 'Nguyễn Văn A',
                    'cohort': '2024',
                    'class_name': 'CNTT01',
                    'password': 'Password@123',
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = CreateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()

        return Response(
            UserProfileSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class AdminBatchCreateAccountView(APIView):
    """
    Admin-only endpoint to create multiple user accounts in a single request.
    The request body is a JSON array of account objects.
    """
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Admin'],
        operation_id='adminBatchCreateAccount',
        summary='Tạo hàng loạt tài khoản người dùng (Admin)',
        description=(
            'Tạo nhiều tài khoản cùng lúc. '
            'Body là một JSON array các object tài khoản (cùng định dạng với API tạo đơn lẻ). '
            'Nếu bất kỳ tài khoản nào không hợp lệ, toàn bộ batch sẽ bị huỷ (atomic).'
        ),
        request=BatchCreateAccountSerializer,
        responses={
            201: UserProfileSerializer(many=True),
            400: {'description': 'Dữ liệu không hợp lệ'},
            403: {'description': 'Không có quyền truy cập'},
        },
        examples=[
            OpenApiExample(
                'Batch Create Accounts',
                value={
                    'accounts': [
                        {
                            'username': 'sv2024001',
                            'name': 'Nguyễn Văn A',
                            'cohort': '2024',
                            'class_name': 'CNTT01',
                            'password': 'Password@123',
                        },
                        {
                            'username': 'sv2024002',
                            'name': 'Trần Thị B',
                            'cohort': '2024',
                            'class_name': 'CNTT01',
                            'password': 'Password@456',
                        },
                    ]
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = BatchCreateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            users = serializer.save()

        return Response(
            UserProfileSerializer(users, many=True).data,
            status=status.HTTP_201_CREATED,
        )
