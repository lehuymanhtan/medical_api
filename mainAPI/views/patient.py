"""
Doctor Workflow Views (Patient Lookup)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from mainAPI.models import User, Examination, AuditLog
from mainAPI.serializers.user import PatientSummarySerializer
from mainAPI.serializers.examination import ExaminationSummarySerializer
from mainAPI.permissions import IsDoctor


class PatientViewSet(viewsets.GenericViewSet):
    """
    Patient lookup and history views for doctors
    """
    permission_classes = [IsDoctor]
    
    @action(detail=False, methods=['get'], url_path='lookup')
    def lookup(self, request):
        """
        GET /patients/lookup?qr_code={uuid}
        QR code lookup for patient information
        """
        qr_code = request.query_params.get('qr_code')
        
        if not qr_code:
            return Response(
                {'error': 'qr_code parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Look up patient by UUID (QR code contains user ID)
        patient = get_object_or_404(User, id=qr_code, role='STUDENT')
        
        # Create audit log for QR scan
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.PATIENT_QR_SCANNED,
            model_name='User',
            object_id=patient.id,
            object_repr=str(patient),
            additional_data={'patient_id': str(patient.id)},
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Return patient summary
        serializer = PatientSummarySerializer(patient)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='examinations')
    def examinations(self, request, pk=None):
        """
        GET /patients/{id}/examinations
        Get full examination history for a patient
        """
        patient = get_object_or_404(User, id=pk, role='STUDENT')
        
        # Create audit log for history access
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.PATIENT_HISTORY_VIEWED,
            model_name='User',
            object_id=patient.id,
            object_repr=str(patient),
            additional_data={'patient_id': str(patient.id)},
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Get examinations
        examinations = Examination.objects.filter(
            patient=patient
        ).select_related('doctor').order_by('-examination_date')
        
        serializer = ExaminationSummarySerializer(examinations, many=True)
        return Response(serializer.data)
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
