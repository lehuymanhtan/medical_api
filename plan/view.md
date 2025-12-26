# Django Views Plan - Medical Management System

## Overview
This document outlines the Django REST Framework views architecture for the University Healthcare Management System based on the API specification (api.yaml v1.0.0) and the models plan (model.md).

## Architecture Approach
- **Django REST Framework (DRF)**: ViewSets and APIViews
- **RBAC Implementation**: Custom permission classes
- **Authentication**: JWT via SimpleJWT
- **Serializers**: Nested and context-aware serializers
- **Business Logic**: Service layer where appropriate

---

## File Structure

```
mainAPI/
├── views/
│   ├── __init__.py
│   ├── auth.py           # Authentication endpoints
│   ├── user.py           # User profile and dashboard
│   ├── patient.py        # Doctor workflow (QR lookup, patient history)
│   ├── appointment.py    # Appointment management
│   ├── examination.py    # Examination workflow
│   ├── ticket.py         # Ticket/consulting system
│   └── utility.py        # File upload utilities
├── serializers/
│   ├── __init__.py
│   ├── user.py
│   ├── patient.py
│   ├── appointment.py
│   ├── examination.py
│   └── ticket.py
├── permissions.py        # Custom permission classes
├── services.py           # Business logic layer
└── utils.py              # Helper functions
```

---

## Custom Permission Classes

### File: `mainAPI/permissions.py`

```python
from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """
    Permission for student-only endpoints
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'STUDENT'

class IsDoctor(permissions.BasePermission):
    """
    Permission for doctor-only endpoints
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['DOCTOR', 'ADMIN']

class IsAdmin(permissions.BasePermission):
    """
    Permission for admin-only endpoints
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

class IsOwnerOrDoctor(permissions.BasePermission):
    """
    Allow owners to access their own data, or doctors to access patient data
    """
    def has_object_permission(self, request, view, obj):
        # Doctors can access any patient data
        if request.user.role in ['DOCTOR', 'ADMIN']:
            return True
        # Students can only access their own data
        if hasattr(obj, 'patient'):
            return obj.patient == request.user
        return obj.user == request.user or obj == request.user

class CanCancelOwnAppointment(permissions.BasePermission):
    """
    Students can cancel their own pending appointments
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'STUDENT':
            return obj.patient == request.user and obj.status == 'PENDING'
        return request.user.role in ['DOCTOR', 'ADMIN']
```

---

## Views Implementation

### 1. Authentication Views

**File**: `mainAPI/views/auth.py`

**Endpoints**:
- `POST /auth/login`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from mainAPI.serializers.user import UserProfileSerializer
from mainAPI.models import AuditLog

class LoginView(APIView):
    """
    POST /auth/login
    Public endpoint for user authentication
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Log authentication
        AuditLog.objects.create(
            user=user,
            action='USER_LOGIN',
            model_name='User',
            object_id=user.id,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user, context={'request': request}).data
        })
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

**Key Points**:
- Public endpoint (AllowAny)
- JWT token generation
- Audit log creation
- IP address tracking
- Returns user profile with token

---

### 2. User Profile & Dashboard Views

**File**: `mainAPI/views/user.py`

**Endpoints**:
- `GET /users/me`
- `GET /users/me/medical-summary`
- `GET /users/me/examinations`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from mainAPI.models import User, Examination
from mainAPI.serializers.user import (
    UserProfileSerializer,
    PatientSummarySerializer
)
from mainAPI.serializers.examination import ExaminationSummarySerializer
from mainAPI.permissions import IsStudent

class UserProfileViewSet(viewsets.GenericViewSet):
    """
    User profile and self-service endpoints
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    @action(detail=False, methods=['get'], url_path='me')
    def get_current_user(self, request):
        """
        GET /users/me
        Returns current user profile with QR code UUID
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='me/medical-summary',
        permission_classes=[IsAuthenticated, IsStudent]
    )
    def medical_summary(self, request):
        """
        GET /users/me/medical-summary
        Returns patient medical summary (students only)
        """
        if not hasattr(request.user, 'patient_profile'):
            return Response(
                {'error': 'No patient profile found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PatientSummarySerializer(
            request.user,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='me/examinations'
    )
    def my_examinations(self, request):
        """
        GET /users/me/examinations
        Returns user's examination history
        """
        examinations = Examination.objects.filter(
            patient=request.user,
            status='COMPLETED'
        ).select_related('doctor').order_by('-examination_date')
        
        serializer = ExaminationSummarySerializer(
            examinations,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
```

**Key Points**:
- Custom actions using `@action` decorator
- Role-based permission on medical-summary
- Query optimization with select_related
- Context-aware serializers

---

### 3. Doctor Workflow Views (Patient Lookup)

**File**: `mainAPI/views/patient.py`

**Endpoints**:
- `GET /patients/lookup?qr_code={uuid}`
- `GET /patients/{id}/examinations`

```python
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
    Doctor workflow endpoints for patient management
    """
    permission_classes = [IsDoctor]
    queryset = User.objects.filter(role='STUDENT')
    
    @action(detail=False, methods=['get'], url_path='lookup')
    def qr_lookup(self, request):
        """
        GET /patients/lookup?qr_code={uuid}
        QR code scan to retrieve patient information
        """
        qr_code = request.query_params.get('qr_code')
        
        if not qr_code:
            return Response(
                {'error': 'qr_code parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        patient = get_object_or_404(
            User.objects.select_related('patient_profile'),
            id=qr_code,
            role='STUDENT',
            is_active=True
        )
        
        # Log QR scan access
        AuditLog.objects.create(
            user=request.user,
            action='QR_SCAN_LOOKUP',
            model_name='User',
            object_id=patient.id,
            object_repr=patient.full_name,
            additional_data={'qr_code': str(qr_code)},
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        serializer = PatientSummarySerializer(
            patient,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['get'],
        url_path='examinations'
    )
    def patient_examinations(self, request, pk=None):
        """
        GET /patients/{id}/examinations
        View complete examination history of a specific patient
        """
        patient = self.get_object()
        
        # Log patient history access
        AuditLog.objects.create(
            user=request.user,
            action='PATIENT_HISTORY_VIEWED',
            model_name='User',
            object_id=patient.id,
            object_repr=patient.full_name,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        examinations = Examination.objects.filter(
            patient=patient,
            status='COMPLETED'
        ).select_related('doctor').prefetch_related('attachments')
        
        serializer = ExaminationSummarySerializer(
            examinations,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

**Key Points**:
- QR lookup via UUID
- Audit logging for all patient data access
- Query optimization (select_related, prefetch_related)
- 404 handling with get_object_or_404
- IP tracking for security

---

### 4. Appointment Management Views

**File**: `mainAPI/views/appointment.py`

**Endpoints**:
- `GET /appointments`
- `POST /appointments`
- `PATCH /appointments/{id}`

```python
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import IntegrityError
from django.utils import timezone
from mainAPI.models import Appointment, AuditLog
from mainAPI.serializers.appointment import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentPatchSerializer
)
from mainAPI.permissions import IsStudent, CanCancelOwnAppointment

class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Appointment booking and management
    """
    serializer_class = AppointmentSerializer
    
    def get_queryset(self):
        """
        Filter appointments based on user role
        - Students see their own appointments
        - Doctors/Admins see all appointments (or their assigned ones)
        """
        user = self.request.user
        
        if user.role == 'STUDENT':
            return Appointment.objects.filter(
                patient=user
            ).order_by('-appointment_date')
        
        # Doctors see all appointments (can be filtered later by assignment)
        queryset = Appointment.objects.select_related(
            'patient',
            'cancelled_by'
        ).order_by('-appointment_date')
        
        # Optional date filter
        date_filter = self.request.query_params.get('date')
        if date_filter:
            queryset = queryset.filter(appointment_date=date_filter)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action == 'partial_update':
            return AppointmentPatchSerializer
        return AppointmentSerializer
    
    def get_permissions(self):
        """
        Students can create and cancel their own
        Doctors/Admins can view and update all
        """
        if self.action == 'create':
            return [IsStudent()]
        elif self.action == 'partial_update':
            return [CanCancelOwnAppointment()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """
        POST /appointments
        Students book appointment for a specific date
        One appointment per patient per day constraint
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            appointment = serializer.save(
                patient=request.user,
                status='PENDING'
            )
            
            # Log appointment creation
            AuditLog.objects.create(
                user=request.user,
                action='APPOINTMENT_CREATED',
                model_name='Appointment',
                object_id=appointment.id,
                object_repr=f"Appointment on {appointment.appointment_date}",
                additional_data={
                    'appointment_date': str(appointment.appointment_date),
                    'reason': appointment.reason
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
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
    
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /appointments/{id}
        Cancel or reschedule appointment
        """
        appointment = self.get_object()
        serializer = self.get_serializer(
            appointment,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        
        # Handle cancellation
        if 'status' in request.data and request.data['status'] == 'CANCELLED':
            serializer.save(
                cancelled_by=request.user,
                cancellation_reason=request.data.get('cancellation_reason', '')
            )
            
            AuditLog.objects.create(
                user=request.user,
                action='APPOINTMENT_CANCELLED',
                model_name='Appointment',
                object_id=appointment.id,
                additional_data={
                    'cancellation_reason': request.data.get('cancellation_reason', ''),
                    'cancelled_by_role': request.user.role
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        # Handle completion (doctors only)
        elif 'status' in request.data and request.data['status'] == 'COMPLETED':
            serializer.save()
            
            AuditLog.objects.create(
                user=request.user,
                action='APPOINTMENT_COMPLETED',
                model_name='Appointment',
                object_id=appointment.id,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        # Handle date change
        else:
            try:
                serializer.save()
            except IntegrityError:
                return Response(
                    {'error': 'An appointment already exists on the new date'},
                    status=status.HTTP_409_CONFLICT
                )
        
        return Response(AppointmentSerializer(appointment).data)
    
    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

**Key Points**:
- Role-based queryset filtering
- One appointment per day constraint handling
- Audit logging for all state changes
- Support for cancellation and rescheduling
- Custom permissions per action

---

### 5. Examination Workflow Views

**File**: `mainAPI/views/examination.py`

**Endpoints**:
- `POST /examinations`
- `PUT /examinations/{id}`
- `POST /examinations/{id}/finalize`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from mainAPI.models import Examination, Appointment, AuditLog
from mainAPI.serializers.examination import (
    ExaminationSerializer,
    ExaminationCreateSerializer,
    ExaminationUpdateSerializer,
    ExaminationFinalizeSerializer
)
from mainAPI.permissions import IsDoctor

class ExaminationViewSet(viewsets.ModelViewSet):
    """
    Medical examination workflow
    """
    permission_classes = [IsDoctor]
    serializer_class = ExaminationSerializer
    queryset = Examination.objects.select_related(
        'patient',
        'doctor',
        'appointment'
    ).prefetch_related('attachments')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ExaminationCreateSerializer
        elif self.action == 'update':
            return ExaminationUpdateSerializer
        elif self.action == 'finalize':
            return ExaminationFinalizeSerializer
        return ExaminationSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        POST /examinations
        Start new examination session
        Links to appointment and marks it as completed
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        appointment = serializer.validated_data.get('appointment')
        
        # Verify appointment doesn't already have examination
        if hasattr(appointment, 'examination'):
            return Response(
                {'error': 'This appointment already has an examination record'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create examination
        examination = serializer.save(
            doctor=request.user,
            status='DRAFT'
        )
        
        # Update appointment status
        if appointment:
            appointment.status = 'COMPLETED'
            appointment.save()
        
        # Log examination creation
        AuditLog.objects.create(
            user=request.user,
            action='EXAMINATION_CREATED',
            model_name='Examination',
            object_id=examination.id,
            object_repr=f"Examination for {examination.patient.full_name}",
            additional_data={
                'patient_id': str(examination.patient.id),
                'appointment_id': str(appointment.id) if appointment else None
            },
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response(
            ExaminationSerializer(examination).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        PUT /examinations/{id}
        Update examination record (only in DRAFT status)
        """
        examination = self.get_object()
        
        if examination.status == 'COMPLETED':
            return Response(
                {'error': 'Cannot update finalized examination'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store old data for audit log
        old_data = {
            'symptoms': examination.symptoms,
            'initial_diagnosis': examination.initial_diagnosis,
            'notes': examination.notes
        }
        
        serializer = self.get_serializer(
            examination,
            data=request.data,
            partial=False
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Log update
        AuditLog.objects.create(
            user=request.user,
            action='EXAMINATION_UPDATED',
            model_name='Examination',
            object_id=examination.id,
            changes={'old': old_data, 'new': request.data},
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response(ExaminationSerializer(examination).data)
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def finalize(self, request, pk=None):
        """
        POST /examinations/{id}/finalize
        Lock examination record (irreversible)
        """
        examination = self.get_object()
        
        if examination.status == 'COMPLETED':
            return Response(
                {'error': 'Examination is already finalized'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(
            examination,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        
        # Validate required fields
        if not serializer.validated_data.get('final_diagnosis'):
            return Response(
                {'error': 'final_diagnosis is required to finalize'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not serializer.validated_data.get('prescription'):
            return Response(
                {'error': 'prescription is required to finalize'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Finalize examination
        examination = serializer.save(
            status='COMPLETED',
            finalized_at=timezone.now()
        )
        
        # Log finalization
        AuditLog.objects.create(
            user=request.user,
            action='EXAMINATION_FINALIZED',
            model_name='Examination',
            object_id=examination.id,
            object_repr=f"Finalized examination for {examination.patient.full_name}",
            additional_data={
                'final_diagnosis': examination.final_diagnosis,
                'prescription': examination.prescription,
                'finalized_at': examination.finalized_at.isoformat()
            },
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response(ExaminationSerializer(examination).data)
    
    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

**Key Points**:
- Draft/Finalize workflow enforcement
- Atomic transactions for data consistency
- Appointment status update on examination creation
- Immutability after finalization
- Comprehensive audit logging
- Change tracking in audit logs

---

### 6. Ticket System Views

**File**: `mainAPI/views/ticket.py`

**Endpoints**:
- `GET /tickets`
- `POST /tickets`
- `GET /tickets/{id}`
- `POST /tickets/{id}/close`
- `POST /tickets/{id}/replies`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from mainAPI.models import Ticket, TicketReply, AuditLog
from mainAPI.serializers.ticket import (
    TicketSerializer,
    TicketDetailSerializer,
    TicketCreateSerializer,
    TicketReplySerializer
)
from mainAPI.permissions import IsStudent, IsDoctor

class TicketViewSet(viewsets.ModelViewSet):
    """
    Support ticket system
    """
    serializer_class = TicketSerializer
    
    def get_queryset(self):
        """
        Filter tickets based on user role
        - Students see their own tickets
        - Doctors/Admins see assigned tickets or all
        """
        user = self.request.user
        
        if user.role == 'STUDENT':
            return Ticket.objects.filter(
                creator=user
            ).select_related(
                'creator',
                'assigned_to',
                'related_appointment'
            ).order_by('-created_at')
        
        # Doctors/Admins see all or assigned tickets
        queryset = Ticket.objects.select_related(
            'creator',
            'assigned_to',
            'related_appointment'
        ).order_by('-created_at')
        
        # Optional status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TicketDetailSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        return TicketSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsStudent()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """
        POST /tickets
        Students create support ticket
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract content for first reply
        content = serializer.validated_data.pop('content')
        
        # Create ticket
        ticket = serializer.save(
            creator=request.user,
            status='OPEN'
        )
        
        # Create first reply (ticket description)
        TicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            content=content,
            is_staff_reply=False
        )
        
        ticket.last_reply_at = timezone.now()
        ticket.save()
        
        # Log ticket creation
        AuditLog.objects.create(
            user=request.user,
            action='TICKET_CREATED',
            model_name='Ticket',
            object_id=ticket.id,
            object_repr=ticket.subject,
            additional_data={'subject': ticket.subject},
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response(
            TicketDetailSerializer(ticket).data,
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /tickets/{id}
        View ticket details with conversation history
        """
        ticket = self.get_object()
        
        # Update last_reply_at to prevent auto-close
        ticket.last_reply_at = timezone.now()
        ticket.save(update_fields=['last_reply_at'])
        
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def close(self, request, pk=None):
        """
        POST /tickets/{id}/close
        Close ticket (mark as RESOLVED)
        """
        ticket = self.get_object()
        
        if ticket.status == 'RESOLVED':
            return Response(
                {'error': 'Ticket is already closed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticket.status = 'RESOLVED'
        ticket.resolved_at = timezone.now()
        ticket.save()
        
        # Log closure
        AuditLog.objects.create(
            user=request.user,
            action='TICKET_CLOSED',
            model_name='Ticket',
            object_id=ticket.id,
            additional_data={
                'closed_by_role': request.user.role,
                'resolved_at': ticket.resolved_at.isoformat()
            },
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'message': 'Ticket closed successfully'})
    
    @action(detail=True, methods=['post'], url_path='replies')
    @transaction.atomic
    def add_reply(self, request, pk=None):
        """
        POST /tickets/{id}/replies
        Add reply to ticket
        """
        ticket = self.get_object()
        
        if ticket.status == 'RESOLVED':
            return Response(
                {'error': 'Cannot reply to closed ticket'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        content = request.data.get('content')
        if not content:
            return Response(
                {'error': 'content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create reply
        is_staff = request.user.role in ['DOCTOR', 'ADMIN']
        reply = TicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            content=content,
            is_staff_reply=is_staff,
            attachment_url=request.data.get('attachment_url', '')
        )
        
        # Update ticket status and timestamp
        if is_staff:
            ticket.status = 'PENDING'
        ticket.last_reply_at = timezone.now()
        ticket.save()
        
        return Response(
            TicketReplySerializer(reply).data,
            status=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

**Key Points**:
- Role-based ticket visibility
- First reply created with ticket
- Auto-close prevention when viewing
- Status transitions (OPEN → PENDING → RESOLVED)
- Timestamp tracking for auto-close logic
- Atomic transactions for consistency

---

### 7. Utility Views (File Upload)

**File**: `mainAPI/views/utility.py`

**Endpoints**:
- `POST /upload/image`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from mainAPI.models import UploadedFile
from mainAPI.serializers.utility import ImageUploadSerializer
import magic

class ImageUploadView(APIView):
    """
    POST /upload/image
    Upload image files only (jpg, jpeg, png)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def post(self, request):
        file_obj = request.FILES.get('file')
        
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size
        if file_obj.size > self.MAX_FILE_SIZE:
            return Response(
                {'error': f'File size exceeds {self.MAX_FILE_SIZE / 1024 / 1024}MB limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate MIME type
        mime_type = magic.from_buffer(file_obj.read(2048), mime=True)
        file_obj.seek(0)  # Reset file pointer
        
        if mime_type not in self.ALLOWED_MIME_TYPES:
            return Response(
                {'error': f'Invalid file type. Allowed: {", ".join(self.ALLOWED_MIME_TYPES)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create upload record
        uploaded_file = UploadedFile.objects.create(
            uploaded_by=request.user,
            file=file_obj,
            file_name=file_obj.name,
            file_size=file_obj.size,
            mime_type=mime_type,
            url=request.build_absolute_uri(f'/media/{file_obj.name}')
        )
        
        serializer = ImageUploadSerializer(uploaded_file)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

**Key Points**:
- MultiPart file upload support
- MIME type validation using python-magic
- File size limit enforcement
- Absolute URL generation
- Secure file handling

---

## Serializers Overview

### File: `mainAPI/serializers/user.py`

```python
from rest_framework import serializers
from mainAPI.models import User, PatientProfile

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile
    """
    class Meta:
        model = User
        fields = ['id', 'full_name', 'role', 'student_id', 'phone_number', 'email']
        read_only_fields = ['id', 'role']

class PatientSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for patient medical summary
    Includes last diagnosis and last visit date
    """
    blood_type = serializers.CharField(source='patient_profile.blood_type')
    allergies = serializers.SerializerMethodField()
    last_diagnosis = serializers.SerializerMethodField()
    last_visit_date = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'blood_type',
            'allergies',
            'last_diagnosis',
            'last_visit_date'
        ]
    
    def get_allergies(self, obj):
        if hasattr(obj, 'patient_profile') and obj.patient_profile.allergies:
            return obj.patient_profile.allergies.split(',')
        return []
    
    def get_last_diagnosis(self, obj):
        last_exam = obj.examinations.filter(
            status='COMPLETED'
        ).order_by('-examination_date').first()
        
        return last_exam.final_diagnosis if last_exam else None
    
    def get_last_visit_date(self, obj):
        last_exam = obj.examinations.filter(
            status='COMPLETED'
        ).order_by('-examination_date').first()
        
        return last_exam.examination_date.date() if last_exam else None
```

### File: `mainAPI/serializers/appointment.py`

```python
from rest_framework import serializers
from mainAPI.models import Appointment

class AppointmentSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient_id',
            'appointment_date',
            'status',
            'reason',
            'cancellation_reason',
            'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']

class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'reason']
    
    def validate_appointment_date(self, value):
        # Ensure date is not in the past
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Cannot book appointment in the past")
        return value

class AppointmentPatchSerializer(serializers.ModelSerializer):
    new_appointment_date = serializers.DateField(
        source='appointment_date',
        required=False
    )
    
    class Meta:
        model = Appointment
        fields = [
            'status',
            'new_appointment_date',
            'cancellation_reason'
        ]
    
    def validate_status(self, value):
        if value not in ['COMPLETED', 'CANCELLED']:
            raise serializers.ValidationError(
                "Status can only be updated to COMPLETED or CANCELLED"
            )
        return value
```

### File: `mainAPI/serializers/examination.py`

```python
from rest_framework import serializers
from mainAPI.models import Examination

class ExaminationSummarySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    date = serializers.DateTimeField(source='examination_date', read_only=True)
    diagnosis_short = serializers.SerializerMethodField()
    
    class Meta:
        model = Examination
        fields = [
            'id',
            'date',
            'doctor_name',
            'diagnosis_short',
            'status'
        ]
    
    def get_diagnosis_short(self, obj):
        diagnosis = obj.final_diagnosis or obj.initial_diagnosis
        return diagnosis[:100] + '...' if diagnosis and len(diagnosis) > 100 else diagnosis

class ExaminationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Examination
        fields = '__all__'
        read_only_fields = [
            'id',
            'doctor',
            'status',
            'examination_date',
            'finalized_at',
            'created_at',
            'updated_at'
        ]

class ExaminationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Examination
        fields = ['patient', 'appointment', 'symptoms', 'initial_diagnosis', 'notes']

class ExaminationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Examination
        fields = [
            'symptoms',
            'initial_diagnosis',
            'notes',
            'blood_pressure',
            'heart_rate',
            'temperature',
            'weight',
            'height'
        ]

class ExaminationFinalizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Examination
        fields = ['final_diagnosis', 'prescription', 'notes']
```

### File: `mainAPI/serializers/ticket.py`

```python
from rest_framework import serializers
from mainAPI.models import Ticket, TicketReply

class TicketReplySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    
    class Meta:
        model = TicketReply
        fields = [
            'author_name',
            'content',
            'created_at',
            'is_staff_reply',
            'attachment_url'
        ]
        read_only_fields = ['author_name', 'created_at', 'is_staff_reply']

class TicketSerializer(serializers.ModelSerializer):
    last_reply = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id',
            'subject',
            'status',
            'related_appointment_id',
            'created_at',
            'last_reply'
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def get_last_reply(self, obj):
        last = obj.replies.order_by('-created_at').first()
        return last.content[:50] + '...' if last and len(last.content) > 50 else last.content if last else None

class TicketDetailSerializer(serializers.ModelSerializer):
    replies = TicketReplySerializer(many=True, read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id',
            'subject',
            'status',
            'related_appointment_id',
            'created_at',
            'last_reply_at',
            'resolved_at',
            'replies'
        ]
        read_only_fields = [
            'id',
            'status',
            'created_at',
            'last_reply_at',
            'resolved_at'
        ]

class TicketCreateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(write_only=True)
    
    class Meta:
        model = Ticket
        fields = ['subject', 'content', 'related_appointment']
```

---

## URL Configuration

### File: `mainAPI/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mainAPI.views.auth import LoginView
from mainAPI.views.user import UserProfileViewSet
from mainAPI.views.patient import PatientViewSet
from mainAPI.views.appointment import AppointmentViewSet
from mainAPI.views.examination import ExaminationViewSet
from mainAPI.views.ticket import TicketViewSet
from mainAPI.views.utility import ImageUploadView

# Create router
router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'examinations', ExaminationViewSet, basename='examination')
router.register(r'tickets', TicketViewSet, basename='ticket')

urlpatterns = [
    # Auth
    path('auth/login', LoginView.as_view(), name='login'),
    
    # User profile
    path('users/', include([
        path('me', UserProfileViewSet.as_view({'get': 'get_current_user'}), name='user-me'),
        path('me/medical-summary', UserProfileViewSet.as_view({'get': 'medical_summary'}), name='user-medical-summary'),
        path('me/examinations', UserProfileViewSet.as_view({'get': 'my_examinations'}), name='user-examinations'),
    ])),
    
    # Patient management (Doctor workflow)
    path('patients/', include([
        path('lookup', PatientViewSet.as_view({'get': 'qr_lookup'}), name='patient-lookup'),
        path('<uuid:pk>/examinations', PatientViewSet.as_view({'get': 'patient_examinations'}), name='patient-examinations'),
    ])),
    
    # Utility
    path('upload/image', ImageUploadView.as_view(), name='upload-image'),
    
    # Router URLs
    path('', include(router.urls)),
]
```

---

## Background Tasks (Celery)

### File: `mainAPI/tasks.py`

```python
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from mainAPI.models import Ticket

@shared_task
def auto_close_inactive_tickets():
    """
    Auto-close tickets with no reply in 15 minutes
    Runs every 5 minutes via Celery Beat
    """
    threshold = timezone.now() - timedelta(minutes=15)
    
    tickets_to_close = Ticket.objects.filter(
        status__in=['OPEN', 'PENDING'],
        last_reply_at__lt=threshold
    )
    
    count = tickets_to_close.count()
    
    tickets_to_close.update(
        status='RESOLVED',
        resolved_at=timezone.now()
    )
    
    return f"Auto-closed {count} tickets"
```

---

## Testing Strategy

### Unit Tests

```python
# mainAPI/tests/test_views.py

from django.test import TestCase
from rest_framework.test import APIClient
from mainAPI.models import User, Appointment

class AppointmentViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username='student1',
            password='test123',
            role='STUDENT',
            student_id='S001'
        )
        self.client.force_authenticate(user=self.student)
    
    def test_create_appointment(self):
        data = {
            'appointment_date': '2025-12-27',
            'reason': 'Regular checkup'
        }
        response = self.client.post('/api/v1/appointments', data)
        self.assertEqual(response.status_code, 201)
    
    def test_duplicate_appointment_same_day(self):
        # Create first appointment
        Appointment.objects.create(
            patient=self.student,
            appointment_date='2025-12-27',
            reason='First'
        )
        
        # Try to create second
        data = {
            'appointment_date': '2025-12-27',
            'reason': 'Second'
        }
        response = self.client.post('/api/v1/appointments', data)
        self.assertEqual(response.status_code, 409)
```

---

## Performance Optimization

### Query Optimization Checklist

1. **Select Related**: Use for ForeignKey lookups
2. **Prefetch Related**: Use for reverse ForeignKey and ManyToMany
3. **Only/Defer**: Select specific fields when needed
4. **Database Indexes**: Already defined in models
5. **Pagination**: Implement for list endpoints
6. **Caching**: Use Redis for frequently accessed data

### Example Optimized Query

```python
# Bad (N+1 query problem)
examinations = Examination.objects.all()
for exam in examinations:
    print(exam.patient.full_name)  # Extra query per iteration

# Good (single query with join)
examinations = Examination.objects.select_related('patient', 'doctor')
for exam in examinations:
    print(exam.patient.full_name)  # No extra query
```

---

## Security Considerations

### 1. JWT Token Security
- Access token: 8 hours lifetime
- Refresh token: 7 days lifetime
- Blacklist on logout (requires djangorestframework-simplejwt)

### 2. Rate Limiting
```python
from rest_framework.throttling import UserRateThrottle

class BurstRateThrottle(UserRateThrottle):
    rate = '100/hour'

class SustainedRateThrottle(UserRateThrottle):
    rate = '1000/day'
```

### 3. Input Validation
- All serializers have field validation
- Custom validators for business rules
- MIME type validation for file uploads

### 4. Audit Logging
- All sensitive operations logged
- IP address tracking
- User agent tracking
- Change tracking (before/after)

---

## Error Handling

### Custom Exception Handler

```python
# mainAPI/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'error': response.data,
            'status_code': response.status_code
        }
        response.data = custom_response_data
    
    return response
```

### Usage in settings.py

```python
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'mainAPI.exceptions.custom_exception_handler',
}
```

---

## API Endpoint Summary

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/auth/login` | POST | LoginView | Public | User authentication |
| `/users/me` | GET | UserProfileViewSet | Authenticated | Current user profile |
| `/users/me/medical-summary` | GET | UserProfileViewSet | Student | Medical summary |
| `/users/me/examinations` | GET | UserProfileViewSet | Authenticated | User's examinations |
| `/patients/lookup` | GET | PatientViewSet | Doctor | QR code lookup |
| `/patients/{id}/examinations` | GET | PatientViewSet | Doctor | Patient history |
| `/appointments` | GET | AppointmentViewSet | Authenticated | List appointments |
| `/appointments` | POST | AppointmentViewSet | Student | Create appointment |
| `/appointments/{id}` | PATCH | AppointmentViewSet | Owner/Doctor | Update appointment |
| `/examinations` | POST | ExaminationViewSet | Doctor | Create examination |
| `/examinations/{id}` | PUT | ExaminationViewSet | Doctor | Update examination |
| `/examinations/{id}/finalize` | POST | ExaminationViewSet | Doctor | Finalize examination |
| `/tickets` | GET | TicketViewSet | Authenticated | List tickets |
| `/tickets` | POST | TicketViewSet | Student | Create ticket |
| `/tickets/{id}` | GET | TicketViewSet | Authenticated | Ticket details |
| `/tickets/{id}/close` | POST | TicketViewSet | Authenticated | Close ticket |
| `/tickets/{id}/replies` | POST | TicketViewSet | Authenticated | Add reply |
| `/upload/image` | POST | ImageUploadView | Authenticated | Upload image |

---

## Next Steps

1. **Implement serializers** in `mainAPI/serializers/` directory
2. **Create permission classes** in `mainAPI/permissions.py`
3. **Implement views** in `mainAPI/views/` directory
4. **Configure URLs** in `mainAPI/urls.py`
5. **Setup Celery** for background tasks
6. **Write unit tests** for each view
7. **Add pagination** to list endpoints
8. **Implement rate limiting**
9. **Add API documentation** using drf-spectacular
10. **Performance testing** and optimization

---

## Required Dependencies

```txt
# Core
django==4.2.8
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.0

# Database
mysqlclient==2.2.0

# File handling
Pillow==10.1.0
python-magic==0.4.27

# Background tasks
celery==5.3.4
redis==5.0.1

# CORS
django-cors-headers==4.3.1

# API documentation
drf-spectacular==0.27.0

# Rate limiting
django-ratelimit==4.1.0

# Development
django-debug-toolbar==4.2.0
```

---

*Generated: December 26, 2025*  
*Based on: api.yaml v1.0.0 and model.md*
