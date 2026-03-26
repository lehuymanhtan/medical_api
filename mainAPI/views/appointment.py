"""
Appointment Management Views
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import IntegrityError
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from mainAPI.models import Appointment, AuditLog
from mainAPI.serializers.appointment import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentPatchSerializer
)
from mainAPI.permissions import IsStudent, CanCancelOwnAppointment
from rest_framework.permissions import IsAuthenticated


@extend_schema_view(
    retrieve=extend_schema(
        summary='Xem chi tiết lịch hẹn',
        tags=['Scheduling']
    ),
    update=extend_schema(
        summary='cập nhật lịch hẹn có id {id}',
        tags=['Scheduling']
    )
)
class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Appointment management endpoints
    """
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    serializer_class = AppointmentSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            permission_classes = [IsStudent]
        elif self.action in ['partial_update', 'update']:
            permission_classes = [CanCancelOwnAppointment]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        
        if user.role == 'STUDENT':
            # Students see only their own appointments
            return Appointment.objects.filter(patient=user).select_related('patient')
        elif user.role == 'DOCTOR':
            # Doctors see upcoming, non-completed appointments
            return Appointment.objects.filter(
                appointment_date__gte=timezone.now().date()
            ).exclude(
                status='COMPLETED'
            ).select_related('patient')
        elif user.role == 'ADMIN':
            # Admins see all appointments
            return Appointment.objects.all().select_related('patient')
        
        return Appointment.objects.none()
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action in ['partial_update', 'update']:
            return AppointmentPatchSerializer
        return AppointmentSerializer
    
    @extend_schema(
        tags=['Scheduling'],
        operation_id='listAppointments',
        summary='Danh sách lịch hẹn',
        description='''Lấy danh sách lịch hẹn dựa trên vai trò:
- Bệnh nhân xem lịch hẹn của chính họ.
- Bác sĩ xem lịch làm việc của họ.''',
        parameters=[
            OpenApiParameter(
                name='date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Lọc theo ngày hẹn',
                required=False,
            )
        ],
        responses={200: AppointmentSerializer(many=True)}
    )
    def list(self, request):
        """
        GET /appointments
        List appointments with optional date filter
        """
        queryset = self.get_queryset()
        
        # Filter by date if provided
        date_param = request.query_params.get('date')
        if date_param:
            queryset = queryset.filter(appointment_date=date_param)
        
        queryset = queryset.order_by('-appointment_date')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Scheduling'],
        operation_id='createAppointment',
        summary='Đặt lịch hẹn',
        description='''Sinh viên đăng ký để đi khám vào một ngày cụ thể.
Không cần chọn bác sĩ - bác sĩ sẽ được chọn khi tạo phiên khám.
Mỗi sinh viên chỉ được đặt một lịch hẹn mỗi ngày.''',
        request=AppointmentCreateSerializer,
        responses={
            201: AppointmentSerializer,
            409: {'description': 'Xung đột - Đã có lịch hẹn trong ngày này'}
        },
        examples=[
            OpenApiExample(
                'Appointment Request',
                value={
                    'appointment_date': '2025-12-30',
                    'reason': 'Đau đầu và sốt'
                },
                request_only=True,
            )
        ]
    )
    def create(self, request):
        """
        POST /appointments
        Create a new appointment
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            appointment = serializer.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.APPOINTMENT_CREATED,
                model_name='Appointment',
                object_id=appointment.id,
                object_repr=str(appointment),
                additional_data={
                    'appointment_date': str(appointment.appointment_date),
                    'reason': appointment.reason,
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            
            return Response(
                AppointmentSerializer(appointment).data,
                status=status.HTTP_201_CREATED
            )
        except IntegrityError:
            return Response(
                {'error': 'You already have an appointment on this date'},
                status=status.HTTP_409_CONFLICT
            )
    
    @extend_schema(
        tags=['Scheduling'],
        operation_id='updateAppointment',
        summary='Điều chỉnh lịch hẹn (Hủy/Đổi ngày)',
        description='''Cập nhật trạng thái lịch hẹn:
- **Bệnh nhân:** Có thể hủy hoặc đổi ngày lịch hẹn của mình.
- **Bác sĩ/Admin:** Có thể cập nhật trạng thái.''',
        request=AppointmentPatchSerializer,
        responses={200: AppointmentSerializer},
        examples=[
            OpenApiExample(
                'Cancel Appointment',
                value={
                    'status': 'CANCELLED',
                    'cancellation_reason': 'Có việc đột xuất'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Reschedule Appointment',
                value={
                    'new_appointment_date': '2025-12-31'
                },
                request_only=True,
            )
        ]
    )
    def partial_update(self, request, pk=None):
        """
        PATCH /appointments/{id}
        Update appointment (cancel/reschedule)
        """
        appointment = self.get_object()
        serializer = self.get_serializer(appointment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Track changes for audit
        old_status = appointment.status
        old_date = appointment.appointment_date
        
        updated_appointment = serializer.save()
        
        # Determine audit action
        if updated_appointment.status == 'CANCELLED':
            audit_action = AuditLog.Action.APPOINTMENT_CANCELLED
        elif updated_appointment.status == 'COMPLETED':
            audit_action = AuditLog.Action.APPOINTMENT_COMPLETED
        else:
            audit_action = AuditLog.Action.APPOINTMENT_CREATED  # Generic update
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action=audit_action,
            model_name='Appointment',
            object_id=updated_appointment.id,
            object_repr=str(updated_appointment),
            changes={
                'status': {'old': old_status, 'new': updated_appointment.status},
                'date': {'old': str(old_date), 'new': str(updated_appointment.appointment_date)},
            },
            additional_data={
                'cancellation_reason': updated_appointment.cancellation_reason,
            } if updated_appointment.status == 'CANCELLED' else {},
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        return Response(AppointmentSerializer(updated_appointment).data)
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
