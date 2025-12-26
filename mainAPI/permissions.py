"""
Custom permission classes for RBAC (Role-Based Access Control)
"""
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
    Permission for accessing patient data
    - Patients can only access their own data
    - Doctors and admins can access any patient data
    """
    def has_object_permission(self, request, view, obj):
        # Doctors and admins can access
        if request.user.role in ['DOCTOR', 'ADMIN']:
            return True
        
        # Students can only access their own data
        if hasattr(obj, 'patient'):
            return obj.patient == request.user
        
        # For user profile objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user


class CanCancelOwnAppointment(permissions.BasePermission):
    """
    Permission for canceling appointments
    - Students can cancel their own pending appointments
    - Doctors/admins can update any appointment
    """
    def has_object_permission(self, request, view, obj):
        # Doctors and admins have full access
        if request.user.role in ['DOCTOR', 'ADMIN']:
            return True
        
        # Students can only cancel their own pending appointments
        if request.user.role == 'STUDENT':
            return obj.patient == request.user and obj.status == 'PENDING'
        
        return False


class IsTicketParticipant(permissions.BasePermission):
    """
    Permission for ticket access
    - Creator can view/reply to their own tickets
    - Assigned doctor can view/reply
    - Admins can view all tickets
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access all tickets
        if request.user.role == 'ADMIN':
            return True
        
        # Creator can access their own ticket
        if obj.creator == request.user:
            return True
        
        # Assigned doctor can access
        if obj.assigned_to == request.user:
            return True
        
        # Doctors can view all tickets (for assignment)
        if request.user.role == 'DOCTOR':
            return True
        
        return False
