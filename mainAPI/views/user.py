"""
User Profile and Dashboard Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from mainAPI.models import User, Examination
from mainAPI.serializers.user import UserProfileSerializer, PatientSummarySerializer
from mainAPI.serializers.examination import ExaminationSummarySerializer
from mainAPI.permissions import IsStudent


class UserProfileViewSet(viewsets.GenericViewSet):
    """
    User profile and dashboard endpoints
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='me')
    def get_profile(self, request):
        """
        GET /users/me
        Get current user's profile
        """
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='me/medical-summary', permission_classes=[IsStudent])
    def medical_summary(self, request):
        """
        GET /users/me/medical-summary
        Get medical summary for current patient
        Only accessible by students
        """
        serializer = PatientSummarySerializer(request.user)
        return Response(serializer.data)
    
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
