"""
Views package
"""
from .auth import LoginView
from .user import UserProfileViewSet
from .patient import PatientViewSet
from .appointment import AppointmentViewSet
from .examination import ExaminationViewSet
from .ticket import TicketViewSet
from .utility import ImageUploadView

__all__ = [
    'LoginView',
    'UserProfileViewSet',
    'PatientViewSet',
    'AppointmentViewSet',
    'ExaminationViewSet',
    'TicketViewSet',
    'ImageUploadView',
]
