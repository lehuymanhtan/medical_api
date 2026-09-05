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
from mainAPI.models import User
from rest_framework.generics import ListAPIView


class AdminUserListView(ListAPIView):
    """
    Admin-only endpoint to get a list of users on the system with pagination.
    """
    permission_classes = [IsAdmin]
    serializer_class = UserProfileSerializer
    queryset = User.objects.all().order_by('-created_at')

    @extend_schema(
        tags=['Admin'],
        operation_id='adminListUsers',
        summary='Lấy danh sách người dùng (Admin)',
        description='Trả về danh sách người dùng trong hệ thống có phân trang.',
        responses={
            200: UserProfileSerializer,
            403: {'description': 'Không có quyền truy cập'},
        },
        examples=[
            OpenApiExample(
                'Paginated User List',
                value={
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "full_name": "Nguyễn Văn A",
                    "role": "STUDENT",
                    "student_id": "SV2024001",
                    "cohort": "2024",
                    "class_name": "CNTT01",
                    "email": "nva@example.com",
                    "phone_number": "0123456789",
                    "date_of_birth": "2000-01-01",
                    "sex": "MALE",
                    "address": "123 ABC Street",
                    "created_at": "2024-01-01T12:00:00Z"
                },
                response_only=True,
                status_codes=['200'],
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

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
