"""
Examination Workflow Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from mainAPI.models import Examination, AuditLog
from mainAPI.serializers.examination import (
    ExaminationSerializer,
    ExaminationCreateSerializer,
    ExaminationUpdateSerializer,
    ExaminationFinalizeSerializer
)
from mainAPI.permissions import IsDoctor


class ExaminationViewSet(viewsets.ModelViewSet):
    """
    Examination management for doctors
    """
    permission_classes = [IsDoctor]
    queryset = Examination.objects.all().select_related('patient', 'doctor', 'appointment')
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'create':
            return ExaminationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExaminationUpdateSerializer
        elif self.action == 'finalize':
            return ExaminationFinalizeSerializer
        return ExaminationSerializer
    
    def create(self, request):
        """
        POST /examinations
        Create a new examination record
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            examination = serializer.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.EXAMINATION_CREATED,
                model_name='Examination',
                object_id=examination.id,
                object_repr=str(examination),
                additional_data={
                    'patient_id': str(examination.patient.id),
                    'appointment_id': str(examination.appointment.id) if examination.appointment else None,
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        
        return Response(
            ExaminationSerializer(examination).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, pk=None):
        """
        PUT /examinations/{id}
        Update examination (draft only)
        """
        examination = self.get_object()
        
        # Verify doctor owns this examination
        if examination.doctor != request.user and request.user.role != 'ADMIN':
            return Response(
                {'error': 'You can only update your own examinations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(examination, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Track changes
        old_data = {
            'symptoms': examination.symptoms,
            'initial_diagnosis': examination.initial_diagnosis,
            'notes': examination.notes,
        }
        
        updated_examination = serializer.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.EXAMINATION_UPDATED,
            model_name='Examination',
            object_id=updated_examination.id,
            object_repr=str(updated_examination),
            changes={
                'symptoms': {'old': old_data['symptoms'], 'new': updated_examination.symptoms},
                'initial_diagnosis': {'old': old_data['initial_diagnosis'], 'new': updated_examination.initial_diagnosis},
            },
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        return Response(ExaminationSerializer(updated_examination).data)
    
    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, pk=None):
        """
        POST /examinations/{id}/finalize
        Finalize examination (lock record)
        """
        examination = self.get_object()
        
        # Verify doctor owns this examination
        if examination.doctor != request.user and request.user.role != 'ADMIN':
            return Response(
                {'error': 'You can only finalize your own examinations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(examination, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Track before finalization
            old_status = examination.status
            
            finalized_examination = serializer.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.EXAMINATION_FINALIZED,
                model_name='Examination',
                object_id=finalized_examination.id,
                object_repr=str(finalized_examination),
                changes={
                    'status': {'old': old_status, 'new': 'COMPLETED'},
                    'finalized_at': {'old': None, 'new': str(finalized_examination.finalized_at)},
                },
                additional_data={
                    'final_diagnosis': finalized_examination.final_diagnosis,
                    'prescription': finalized_examination.prescription,
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        
        return Response(
            ExaminationSerializer(finalized_examination).data,
            status=status.HTTP_200_OK
        )
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
