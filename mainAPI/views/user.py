"""
User Profile and Dashboard Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from mainAPI.models import User, Examination, PatientProfile
from mainAPI.serializers.user import UserProfileSerializer, PatientSummarySerializer, MedicalSummaryUpdateSerializer
from mainAPI.serializers.examination import ExaminationSummarySerializer
from mainAPI.permissions import IsStudent


class UserProfileViewSet(viewsets.GenericViewSet):
    """
    User profile and dashboard endpoints
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        methods=['GET'],
        tags=['Patient Dashboard'],
        operation_id='getUserProfile',
        summary='Lấy hồ sơ người dùng hiện tại',
        description='Trả về thông tin hồ sơ bao gồm UUID tĩnh để tạo mã QR.',
        responses={200: UserProfileSerializer}
    )
    @extend_schema(
        methods=['POST'],
        tags=['Patient Dashboard'],
        operation_id='updateUserProfile',
        summary='Cập nhật hồ sơ người dùng hiện tại',
        description='Cập nhật thông tin cá nhân. Các trường role, student_id, email, và phone_number không thể thay đổi.',
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: {'description': 'Dữ liệu không hợp lệ'}
        }
    )
    @action(detail=False, methods=['get', 'post'], url_path='me')
    def get_profile(self, request):
        """
        GET, POST /users/me
        Get or update current user's profile
        """
        if request.method == 'POST':
            serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Patient Dashboard'],
        operation_id='getMedicalSummary',
        summary='Lấy tóm tắt y tế cá nhân',
        description='Trả về nhóm máu, các loại dị ứng và thông tin quan trọng khác.',
        responses={200: PatientSummarySerializer}
    )
    @action(detail=False, methods=['get'], url_path='me/medical-summary', permission_classes=[IsStudent])
    def medical_summary(self, request):
        """
        GET /users/me/medical-summary
        Get medical summary for current patient
        Only accessible by students
        """
        serializer = PatientSummarySerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Patient Dashboard'],
        operation_id='getMyExaminations',
        summary='Xem lịch sử khám bệnh của tôi',
        description='Trả về danh sách các lần khám trước đây của người dùng hiện tại.',
        responses={200: ExaminationSummarySerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='me/examinations')
    def my_examinations(self, request):
        """
        GET /users/me/examinations
        Get examination history for current user
        """
        examinations = Examination.objects.filter(
            patient=request.user
        ).select_related('doctor').order_by('-examination_date')
        
        serializer = ExaminationSummarySerializer(examinations, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Patient Dashboard'],
        operation_id='updateMedicalSummary',
        summary='Cập nhật thông tin y tế cá nhân',
        description='Sinh viên có thể cập nhật nhóm máu và dị ứng của mình.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'blood_type': {
                        'type': 'string',
                        'enum': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', ''],
                        'nullable': True,
                        'description': 'Nhóm máu'
                    },
                    'allergies': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'nullable': True,
                        'description': 'Danh sách dị ứng'
                    }
                }
            }
        },
        responses={
            200: PatientSummarySerializer,
            400: {'description': 'Dữ liệu không hợp lệ'},
            403: {'description': 'Chỉ sinh viên mới có thể cập nhật'}
        }
    )
    @action(detail=False, methods=['patch'], url_path='me/medical-summary', permission_classes=[IsStudent])
    def update_medical_summary(self, request):
        """
        PATCH /users/me/medical-summary
        Update medical summary for current student
        """
        user = request.user
        
        # Get or create patient profile
        patient_profile, created = PatientProfile.objects.get_or_create(user=user)
        
        serializer = MedicalSummaryUpdateSerializer(patient_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return updated summary
            summary_serializer = PatientSummarySerializer(user)
            return Response(summary_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
