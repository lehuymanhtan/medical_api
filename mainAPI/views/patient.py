"""
Doctor Workflow Views (Patient Lookup)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from mainAPI.models import User, Examination, AuditLog
from mainAPI.serializers.user import PatientSummarySerializer
from mainAPI.serializers.examination import ExaminationSummarySerializer
from mainAPI.permissions import IsDoctor
from mainAPI.utils.request import get_client_ip


class PatientViewSet(viewsets.GenericViewSet):
    """
    Patient lookup and history views for doctors
    """
    permission_classes = [IsDoctor]
    queryset = User.objects.filter(
        role=User.Role.STUDENT
    ).select_related('patient_profile').prefetch_related('examinations_as_patient')
    
    @extend_schema(
        tags=['Doctor Workflow'],
        operation_id='patientLookup',
        summary='Quét mã QR để tìm bệnh nhân',
        description='Tìm kiếm bệnh nhân bằng UUID được quét từ ứng dụng của sinh viên.',
        parameters=[
            OpenApiParameter(
                name='qr_code',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='UUID được quét từ ứng dụng của sinh viên',
                required=True,
            )
        ],
        responses={
            200: PatientSummarySerializer,
            404: {'description': 'Không tìm thấy bệnh nhân'}
        }
    )
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
        patient = get_object_or_404(self.get_queryset(), id=qr_code)
        
        # Create audit log for QR scan
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.PATIENT_QR_SCANNED,
            model_name='User',
            object_id=patient.id,
            object_repr=str(patient),
            additional_data={'patient_id': str(patient.id)},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Return patient summary
        serializer = PatientSummarySerializer(patient)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Doctor Workflow'],
        operation_id='getPatientExaminations',
        summary='Xem toàn bộ lịch sử của một bệnh nhân cụ thể',
        description='Trả về lịch sử khám bệnh đầy đủ của một bệnh nhân.',
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='ID của bệnh nhân',
                required=True,
            )
        ],
        responses={200: ExaminationSummarySerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='examinations')
    def examinations(self, request, pk=None):
        """
        GET /patients/{id}/examinations
        Get full examination history for a patient
        """
        patient = get_object_or_404(self.get_queryset(), id=pk)
        
        # Create audit log for history access
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.PATIENT_HISTORY_VIEWED,
            model_name='User',
            object_id=patient.id,
            object_repr=str(patient),
            additional_data={'patient_id': str(patient.id)},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # Get examinations
        examinations = Examination.objects.filter(
            patient=patient
        ).select_related('doctor').order_by('-examination_date')
        
        serializer = ExaminationSummarySerializer(examinations, many=True)
        return Response(serializer.data)
