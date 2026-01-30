"""
Examination Workflow Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiExample
from mainAPI.models import Examination, AuditLog
from mainAPI.serializers.examination import (
    ExaminationSerializer,
    ExaminationCreateSerializer,
    ExaminationUpdateSerializer,
    ExaminationFinalizeSerializer
)
from mainAPI.permissions import IsDoctor, IsDoctorOrOwnerReadOnly


class ExaminationViewSet(viewsets.ModelViewSet):
    """
    Examination management
    - Doctors: Full CRUD access
    - Students: Read-only access to their own examinations
    """
    queryset = Examination.objects.all().select_related('patient', 'doctor', 'appointment')
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions that this view requires
        """
        if self.action == 'retrieve':
            # retrieve action allows students to view their own examinations
            permission_classes = [IsDoctorOrOwnerReadOnly]
        else:
            # All other actions require doctor permissions
            permission_classes = [IsDoctor]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'create':
            return ExaminationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExaminationUpdateSerializer
        elif self.action == 'finalize':
            return ExaminationFinalizeSerializer
        return ExaminationSerializer
    
    @extend_schema(
        tags=['Doctor Workflow'],
        operation_id='createExamination',
        summary='Bắt đầu phiên khám bệnh mới',
        description='Tạo một bản ghi khám bệnh mới cho bệnh nhân. appointment_id là tùy chọn (để xử lý trường hợp khẩn cấp).',
        request=ExaminationCreateSerializer,
        responses={201: ExaminationSerializer},
        examples=[
            OpenApiExample(
                'Examination with Appointment',
                value={
                    'patient_id': '123e4567-e89b-12d3-a456-426614174000',
                    'appointment_id': '223e4567-e89b-12d3-a456-426614174000'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Emergency Examination (No Appointment)',
                value={
                    'patient_id': '123e4567-e89b-12d3-a456-426614174000',
                    'symptoms': 'Đau ngực cấp tính',
                    'initial_diagnosis': 'Cần kiểm tra tim mạch ngay'
                },
                request_only=True,
            )
        ]
    )
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
    
    @extend_schema(
        tags=['Doctor Workflow'],
        operation_id='updateExamination',
        summary='Cập nhật kết quả khám (Nháp/Đang xử lý)',
        description='Cập nhật thông tin khám bệnh cho bản ghi ở trạng thái nháp.',
        request=ExaminationUpdateSerializer,
        responses={200: ExaminationSerializer},
        examples=[
            OpenApiExample(
                'Update Examination',
                value={
                    'symptoms': 'Đau đầu, sốt cao, ho khan',
                    'initial_diagnosis': 'Nghi ngờ cảm cúm',
                    'notes': 'Bệnh nhân cần nghỉ ngơi và theo dõi thêm'
                },
                request_only=True,
            )
        ]
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
    
    @extend_schema(
        tags=['Doctor Workflow'],
        operation_id='finalizeExamination',
        summary='Hoàn tất chẩn đoán và khóa hồ sơ',
        description='Hành động không thể hoàn tác. Đặt trạng thái thành COMPLETED và khóa hồ sơ khám bệnh.',
        request=ExaminationFinalizeSerializer,
        responses={200: ExaminationSerializer},
        examples=[
            OpenApiExample(
                'Finalize Examination',
                value={
                    'final_diagnosis': 'Cảm cúm mùa',
                    'prescription': 'Paracetamol 500mg, 3 lần/ngày. Nghỉ ngơi ít nhất 3 ngày.',
                    'notes': 'Tái khám sau 3 ngày nếu triệu chứng không cải thiện'
                },
                request_only=True,
            )
        ]
    )
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
