"""
Views package
"""
from .auth import LoginView, RefreshTokenView
from .user import UserProfileViewSet
from .patient import PatientViewSet
from .appointment import AppointmentViewSet
from .examination import ExaminationViewSet
from .ticket import TicketViewSet
from .utility import ImageUploadView

__all__ = [
    'LoginView',
    'RefreshTokenView',
    'UserProfileViewSet',
    'PatientViewSet',
    'AppointmentViewSet',
    'ExaminationViewSet',
    'TicketViewSet',
    'ImageUploadView',
]
