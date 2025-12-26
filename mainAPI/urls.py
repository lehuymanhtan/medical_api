"""
URL Configuration for mainAPI
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from mainAPI.views import (
    LoginView,
    UserProfileViewSet,
    PatientViewSet,
    AppointmentViewSet,
    ExaminationViewSet,
    TicketViewSet,
    ImageUploadView
)

# Create router for viewsets
router = DefaultRouter()

# Register viewsets
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'examinations', ExaminationViewSet, basename='examination')
router.register(r'tickets', TicketViewSet, basename='ticket')

# URL patterns
urlpatterns = [
    # Authentication
    path('auth/login', LoginView.as_view(), name='login'),
    
    # User profile and dashboard
    path('users/', include([
        path('me', UserProfileViewSet.as_view({'get': 'get_profile'}), name='user-profile'),
        path('me/medical-summary', UserProfileViewSet.as_view({'get': 'medical_summary'}), name='user-medical-summary'),
        path('me/examinations', UserProfileViewSet.as_view({'get': 'my_examinations'}), name='user-examinations'),
    ])),
    
    # Patient lookup (doctor workflow)
    path('patients/', include([
        path('lookup', PatientViewSet.as_view({'get': 'lookup'}), name='patient-lookup'),
        path('<uuid:pk>/examinations', PatientViewSet.as_view({'get': 'examinations'}), name='patient-examinations'),
    ])),
    
    # File upload
    path('upload/image', ImageUploadView.as_view(), name='upload-image'),
    
    # Router URLs (appointments, examinations, tickets)
    path('', include(router.urls)),
]
