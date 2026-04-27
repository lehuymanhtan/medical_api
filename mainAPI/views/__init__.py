"""
Views package
"""
from .auth import LoginView, RefreshTokenView, ChangePasswordView
from .user import UserProfileViewSet
from .patient import PatientViewSet
from .appointment import AppointmentViewSet
from .examination import ExaminationViewSet
from .ticket import TicketViewSet
from .utility import ImageUploadView
from .admin_account import AdminCreateAccountView, AdminBatchCreateAccountView

__all__ = [
    'LoginView',
    'RefreshTokenView',
    'ChangePasswordView',
    'UserProfileViewSet',
    'PatientViewSet',
    'AppointmentViewSet',
    'ExaminationViewSet',
    'TicketViewSet',
    'ImageUploadView',
    'AdminCreateAccountView',
    'AdminBatchCreateAccountView',
]
