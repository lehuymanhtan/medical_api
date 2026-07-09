"""
URL Configuration for mainAPI
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mainAPI.views import (
    LoginView,
    RefreshTokenView,
    ChangePasswordView,
    LogoutView,
    UserProfileViewSet,
    PatientViewSet,
    AppointmentViewSet,
    ExaminationViewSet,
    TicketViewSet,
    ImageUploadView,
    AdminCreateAccountView,
    AdminBatchCreateAccountView,
    ForgotPasswordView,
    ResetPasswordView,
)
from mainAPI.views.queue import QueueEntryViewSet
from mainAPI.views.notification import FCMDeviceTokenViewSet
from mainAPI.views.prescription import PrescriptionViewSet

prescription_list = PrescriptionViewSet.as_view({'get': 'list', 'post': 'create'})
prescription_detail = PrescriptionViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'})

# Create router for viewsets
router = DefaultRouter()

# Register viewsets
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'examinations', ExaminationViewSet, basename='examination')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'queues', QueueEntryViewSet, basename='queue')
router.register(r'registerNotification', FCMDeviceTokenViewSet, basename='notification')

# URL patterns
urlpatterns = [
    # Authentication
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/refresh', RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/change-password', ChangePasswordView.as_view(), name='change-password'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('auth/forgot-password', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password', ResetPasswordView.as_view(), name='reset-password'),
    
    # User profile and dashboard
    path('users/', include([
        path('me', UserProfileViewSet.as_view({'get': 'get_profile', 'post': 'get_profile'}), name='user-profile'),
        path('me/medical-summary', UserProfileViewSet.as_view({
            'get': 'medical_summary',
            'patch': 'update_medical_summary'
        }), name='user-medical-summary'),
        path('me/examinations', UserProfileViewSet.as_view({'get': 'my_examinations'}), name='user-examinations'),
    ])),
    
    # Patient lookup (doctor workflow)
    path('patients/', include([
        path('lookup', PatientViewSet.as_view({'get': 'lookup'}), name='patient-lookup'),
        path('<uuid:pk>/examinations', PatientViewSet.as_view({'get': 'examinations'}), name='patient-examinations'),
    ])),
    
    # File upload
    path('upload/image', ImageUploadView.as_view(), name='upload-image'),
    
    # Admin account management
    path('admin/accounts/create', AdminCreateAccountView.as_view(), name='admin-create-account'),
    path('admin/accounts/batch-create', AdminBatchCreateAccountView.as_view(), name='admin-batch-create-account'),
    
    # Nested routes for medicines
    path('examinations/<uuid:examination_id>/medicines/', prescription_list, name='examination-medicines-list'),
    path('examinations/<uuid:examination_id>/medicines/<uuid:pk>/', prescription_detail, name='examination-medicines-detail'),
    
    # Router URLs (appointments, examinations, tickets)
    path('', include(router.urls)),
]
