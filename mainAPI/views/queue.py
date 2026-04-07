from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Max
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from mainAPI.models import QueueEntry
from mainAPI.serializers.queue import (
    QueueEntrySerializer, 
    QueueEntryCreateSerializer, 
    QueueEntryStatusUpdateSerializer
)
from mainAPI.utils.fcm import send_fcm_notification

@extend_schema_view(
    list=extend_schema(
        tags=['Queue'],
        summary='Danh sách hàng đợi hôm nay',
        description='Lấy danh sách tất cả các số thứ tự được xếp hàng trong ngày hôm nay. Mặc định chỉ lấy các phiếu của ngày hiện tại.'
    ),
    retrieve=extend_schema(
        tags=['Queue'],
        summary='Lấy thông tin chi tiết một số thứ tự',
        description='Xem thông tin chi tiết của một số thứ tự cụ thể trong hàng đợi.'
    ),
    partial_update=extend_schema(
        tags=['Queue'],
        summary='Cập nhật trạng thái số thứ tự',
        description='Bác sĩ/Admin có thể cập nhật các trạng thái (như WAITING, CALLED, CANCELLED).'
    )
)
class QueueEntryViewSet(viewsets.ModelViewSet):
    """
    Queue management endpoints
    """
    http_method_names = ['get', 'post', 'patch']
    
    def get_permissions(self):
        # We allow authenticated users to view the queue and join it.
        # Specific restrictions (e.g. for update or call_patient) are handled in the methods.
        return [IsAuthenticated()]
        
    def get_queryset(self):
        # Filter queue entries by today
        today = timezone.now().date()
        return QueueEntry.objects.filter(date=today).select_related('patient')
        
    def get_serializer_class(self):
        if self.action == 'create':
            return QueueEntryCreateSerializer
        elif self.action in ['partial_update', 'update', 'call_next']:
            return QueueEntryStatusUpdateSerializer
        return QueueEntrySerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.partial_update(request, *args, **kwargs)
        
    def partial_update(self, request, *args, **kwargs):
        user = request.user
        
        # Only Admin and Doctor can manually update using generic patch mechanism
        if user.role not in ['DOCTOR', 'ADMIN']:
            return Response({'error': 'Chỉ nhân viên y tế mới có quyền cập nhật thủ công. Học sinh vui lòng sử dụng API Cancel nếu muốn hủy.'}, status=status.HTTP_403_FORBIDDEN)
                
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=['Queue'],
        summary='Hủy số thứ tự',
        description='Cho phép sinh viên tự hủy số thứ tự của chính mình.',
        request=None,
        responses={200: QueueEntrySerializer}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        queue_entry = self.get_object()
        user = request.user
        
        if user.role != 'STUDENT':
            return Response({'error': 'Chỉ sinh viên mới có thể sử dụng chức năng tự hủy phiếu.'}, status=status.HTTP_403_FORBIDDEN)
            
        if queue_entry.patient != user:
            return Response({'error': 'Bạn chỉ có thể hủy số thứ tự của chính mình.'}, status=status.HTTP_403_FORBIDDEN)
            
        if queue_entry.status != QueueEntry.Status.WAITING:
            return Response({'error': 'Chỉ có thể hủy khi đang chờ khám.'}, status=status.HTTP_400_BAD_REQUEST)
            
        queue_entry.status = QueueEntry.Status.CANCELLED
        queue_entry.save()
        
        return Response(QueueEntrySerializer(queue_entry).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Queue'],
        summary='Lấy số thứ tự',
        description='Bệnh nhân lấy số thứ tự khám bệnh xếp hàng cho ngày hôm nay.'
    )
    def create(self, request, *args, **kwargs):
        user = request.user
        if user.role != 'STUDENT':
            return Response({'error': 'Only students can take a number.'}, status=status.HTTP_403_FORBIDDEN)
            
        today = timezone.now().date()
        
        # Ensure user hasn't already taken a number today that is not cancelled
        existing = QueueEntry.objects.filter(patient=user, date=today).exclude(status='CANCELLED').first()
        if existing:
            return Response(
                {'error': 'You already have a valid number for today.', 'number': existing.number},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            max_number_entry = QueueEntry.objects.filter(date=today).aggregate(Max('number'))
            max_number = max_number_entry['number__max'] or 0
            new_number = max_number + 1
            
            queue_entry = QueueEntry.objects.create(
                patient=user,
                date=today,
                number=new_number,
                status=QueueEntry.Status.WAITING
            )
        
        return Response(QueueEntrySerializer(queue_entry).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=['Queue'],
        summary='Gọi bệnh nhân (Call Next)',
        description='Trạng thái số đang chờ được cập nhật thành CALLED và hệ thống tự động gửi FCM Notification tới điện thoại người dùng. Kèm theo thông báo trước cho bệnh nhân còn cách 5 số.',
        responses={200: QueueEntrySerializer}
    )
    @action(detail=True, methods=['post'])
    def call_patient(self, request, pk=None):
        queue_entry = self.get_object()
        
        # Check permissions for doctor
        if request.user.role not in ['DOCTOR', 'ADMIN']:
            return Response({'error': 'Only staff can call next.'}, status=status.HTTP_403_FORBIDDEN)
            
        if queue_entry.status != QueueEntry.Status.WAITING:
            return Response({'error': 'Can only call waiting patients.'}, status=status.HTTP_400_BAD_REQUEST)
            
        queue_entry.status = QueueEntry.Status.CALLED
        queue_entry.save()
        
        # Send Notification to current called patient
        title = "Đến lượt của bạn!"
        body = f"Xin mời bệnh nhân {queue_entry.patient.full_name} có số thứ tự {queue_entry.number} vào phòng khám."
        send_fcm_notification(queue_entry.patient, title, body, data={'queue_id': str(queue_entry.id)})
        
        # Notification for patient 5 spots away
        upcoming_number = queue_entry.number + 5
        today = timezone.now().date()
        upcoming_entry = QueueEntry.objects.filter(
            date=today, 
            number=upcoming_number, 
            status=QueueEntry.Status.WAITING
        ).first()
        
        if upcoming_entry:
            upcoming_title = "Sắp đến lượt của bạn!"
            upcoming_body = f"Số thứ tự {upcoming_entry.number} sắp được gọi. Vui lòng chuẩn bị di chuyển đến phòng khám."
            send_fcm_notification(upcoming_entry.patient, upcoming_title, upcoming_body, data={'queue_id': str(upcoming_entry.id)})
        
        return Response(QueueEntrySerializer(queue_entry).data, status=status.HTTP_200_OK)
