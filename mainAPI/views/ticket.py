"""
Ticket System Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample
from mainAPI.models import Ticket, TicketReply, AuditLog
from mainAPI.serializers.ticket import (
    TicketSerializer,
    TicketDetailSerializer,
    TicketCreateSerializer,
    TicketReplyCreateSerializer
)
from mainAPI.permissions import IsStudent, IsTicketParticipant
from rest_framework.permissions import IsAuthenticated


class TicketViewSet(viewsets.ModelViewSet):
    """
    Ticket/consulting system endpoints
    """
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            permission_classes = [IsStudent]
        elif self.action in ['retrieve', 'close', 'add_reply']:
            permission_classes = [IsTicketParticipant]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter tickets based on user role"""
        user = self.request.user
        
        if user.role == 'STUDENT':
            # Students see only their own tickets
            return Ticket.objects.filter(creator=user).select_related('creator', 'assigned_to')
        elif user.role == 'DOCTOR':
            # Doctors see assigned tickets and all open tickets
            return Ticket.objects.filter(
                assigned_to=user
            ) | Ticket.objects.filter(status='OPEN')
        elif user.role == 'ADMIN':
            # Admins see all tickets
            return Ticket.objects.all().select_related('creator', 'assigned_to')
        
        return Ticket.objects.none()
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'create':
            return TicketCreateSerializer
        elif self.action == 'retrieve':
            return TicketDetailSerializer
        return TicketSerializer
    
    @extend_schema(
        tags=['Consulting'],
        operation_id='listTickets',
        summary='Danh sách phiếu hỗ trợ',
        description='''Lấy danh sách phiếu hỗ trợ dựa trên vai trò:
- Sinh viên xem phiếu của mình.
- Bác sĩ/Admin xem phiếu được gán hoặc tất cả phiếu.''',
        responses={200: TicketSerializer(many=True)}
    )
    def list(self, request):
        """
        GET /tickets
        List tickets based on user role
        """
        queryset = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Consulting'],
        operation_id='createTicket',
        summary='Tạo phiếu hỗ trợ mới',
        description='Chỉ sinh viên có thể tạo phiếu hỗ trợ.',
        request=TicketCreateSerializer,
        responses={201: TicketDetailSerializer},
        examples=[
            OpenApiExample(
                'Create Ticket',
                value={
                    'subject': 'Hỏi về kết quả xét nghiệm',
                    'content': 'Tôi muốn biết thêm thông tin về kết quả xét nghiệm máu của tôi.',
                    'related_appointment_id': '223e4567-e89b-12d3-a456-426614174000'
                },
                request_only=True,
            )
        ]
    )
    def create(self, request):
        """
        POST /tickets
        Create a new ticket with initial reply
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            ticket = serializer.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.TICKET_CREATED,
                model_name='Ticket',
                object_id=ticket.id,
                object_repr=str(ticket),
                additional_data={
                    'subject': ticket.subject,
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        
        return Response(
            TicketDetailSerializer(ticket).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        tags=['Consulting'],
        operation_id='getTicketDetail',
        summary='Xem chi tiết ticket (bao gồm lịch sử phản hồi)',
        description='Lấy thông tin chi tiết của ticket và tất cả các phản hồi.',
        responses={200: TicketDetailSerializer}
    )
    def retrieve(self, request, pk=None):
        """
        GET /tickets/{id}
        Get ticket details with all replies
        """
        ticket = self.get_object()
        
        # Update last_reply_at to prevent auto-close
        ticket.last_reply_at = timezone.now()
        ticket.save(update_fields=['last_reply_at'])
        
        serializer = TicketDetailSerializer(ticket)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Consulting'],
        operation_id='closeTicket',
        summary='Đóng ticket (Đánh dấu là RESOLVED)',
        description='Đóng phiếu hỗ trợ. Ticket cũng tự động đóng nếu không có reply trong 15 phút.',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Ticket closed successfully'}
                }
            }
        }
    )
    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """
        POST /tickets/{id}/close
        Close a ticket
        """
        ticket = self.get_object()
        
        if ticket.status == 'RESOLVED':
            return Response(
                {'error': 'Ticket is already closed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticket.close()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.TICKET_CLOSED,
            model_name='Ticket',
            object_id=ticket.id,
            object_repr=str(ticket),
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        return Response(
            {'message': 'Ticket closed successfully'},
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        tags=['Consulting'],
        operation_id='replyToTicket',
        summary='Trả lời phiếu hỗ trợ',
        description='Thêm phản hồi vào phiếu hỗ trợ.',
        request=TicketReplyCreateSerializer,
        responses={201: {'description': 'Đã thêm phản hồi'}},
        examples=[
            OpenApiExample(
                'Reply to Ticket',
                value={
                    'content': 'Cảm ơn bạn đã liên hệ. Kết quả xét nghiệm của bạn nằm trong giới hạn bình thường.'
                },
                request_only=True,
            )
        ]
    )
    @action(detail=True, methods=['post'], url_path='replies')
    def add_reply(self, request, pk=None):
        """
        POST /tickets/{id}/replies
        Add a reply to a ticket
        """
        ticket = self.get_object()
        
        if ticket.status == 'RESOLVED':
            return Response(
                {'error': 'Cannot reply to a closed ticket'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TicketReplyCreateSerializer(
            data=request.data,
            context={'request': request, 'ticket': ticket}
        )
        serializer.is_valid(raise_exception=True)
        
        reply = serializer.save()
        
        # Update ticket status if staff replies
        if reply.is_staff_reply and ticket.status == 'OPEN':
            ticket.status = 'IN_PROGRESS'
            ticket.save(update_fields=['status'])
        
        return Response(
            {'message': 'Reply added successfully'},
            status=status.HTTP_201_CREATED
        )
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
