"""
User Profile and Dashboard Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from mainAPI.models import User, Examination
from mainAPI.serializers.user import UserProfileSerializer, PatientSummarySerializer
from mainAPI.serializers.examination import ExaminationSummarySerializer
from mainAPI.permissions import IsStudent


class UserProfileViewSet(viewsets.GenericViewSet):
    """
    User profile and dashboard endpoints
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Patient Dashboard'],
        operation_id='getUserProfile',
        summary='Lấy hồ sơ người dùng hiện tại',
        description='Trả về thông tin hồ sơ bao gồm UUID tĩnh để tạo mã QR.',
        responses={200: UserProfileSerializer}
    )
    @action(detail=False, methods=['get'], url_path='me')
    def get_profile(self, request):
        """
        GET /users/me
        Get current user's profile
        """
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
