from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, PatientProfile, DoctorProfile, Appointment, 
    Examination, Ticket, TicketReply, UploadedFile, AuditLog
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'full_name', 'email', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'full_name', 'student_id']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'email', 'phone_number', 'student_id')}),
        ('Role', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    readonly_fields = ['created_at', 'updated_at', 'date_joined', 'last_login']


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'blood_type', 'created_at']
    list_filter = ['blood_type', 'created_at']
    search_fields = ['user__full_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient', {'fields': ('user',)}),
        ('Medical Information', {'fields': ('blood_type', 'allergies', 'chronic_conditions')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'department', 'created_at']
    list_filter = ['specialization', 'department', 'created_at']
    search_fields = ['user__full_name', 'specialization', 'department']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Doctor', {'fields': ('user',)}),
        ('Professional Information', {'fields': ('specialization', 'department', 'bio')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'appointment_date', 'status', 'created_at']
    list_filter = ['status', 'appointment_date', 'created_at']
    search_fields = ['patient__full_name', 'patient__email', 'reason']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'appointment_date'
    
    fieldsets = (
        ('Appointment Details', {'fields': ('patient', 'appointment_date', 'status', 'reason')}),
        ('Cancellation', {'fields': ('cancelled_by', 'cancellation_reason')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'status', 'examination_date', 'finalized_at']
    list_filter = ['status', 'examination_date', 'finalized_at']
    search_fields = ['patient__full_name', 'doctor__full_name', 'symptoms', 'final_diagnosis']
    readonly_fields = ['examination_date', 'finalized_at', 'created_at', 'updated_at']
    date_hierarchy = 'examination_date'
    
    fieldsets = (
        ('Examination Info', {'fields': ('patient', 'doctor', 'appointment', 'status')}),
        ('Clinical Data', {'fields': ('symptoms', 'initial_diagnosis', 'notes')}),
        ('Final Diagnosis', {'fields': ('final_diagnosis', 'prescription')}),
        ('Vital Signs', {'fields': ('blood_pressure', 'heart_rate', 'temperature', 'weight', 'height')}),
        ('Timestamps', {'fields': ('examination_date', 'finalized_at', 'created_at', 'updated_at')}),
    )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['subject', 'creator', 'assigned_to', 'status', 'created_at', 'resolved_at']
    list_filter = ['status', 'created_at', 'resolved_at']
    search_fields = ['subject', 'creator__full_name', 'assigned_to__full_name']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at', 'last_reply_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Ticket Details', {'fields': ('subject', 'status', 'creator', 'assigned_to')}),
        ('Related', {'fields': ('related_appointment',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'last_reply_at', 'resolved_at')}),
    )


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'is_staff_reply', 'created_at']
    list_filter = ['is_staff_reply', 'created_at']
    search_fields = ['ticket__subject', 'author__full_name', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Reply Info', {'fields': ('ticket', 'author', 'is_staff_reply')}),
        ('Content', {'fields': ('content', 'attachment_url')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'uploaded_by', 'mime_type', 'file_size', 'created_at']
    list_filter = ['mime_type', 'created_at']
    search_fields = ['file_name', 'uploaded_by__full_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('File Info', {'fields': ('file', 'file_name', 'file_size', 'mime_type', 'url')}),
        ('Uploaded By', {'fields': ('uploaded_by',)}),
        ('Associations', {'fields': ('examination', 'ticket_reply')}),
        ('Timestamp', {'fields': ('created_at',)}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'model_name', 'object_repr', 'timestamp', 'ip_address']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__full_name', 'object_repr', 'ip_address']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'object_repr', 
                       'changes', 'additional_data', 'ip_address', 'user_agent', 'timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Action', {'fields': ('action', 'user', 'timestamp')}),
        ('Target Object', {'fields': ('model_name', 'object_id', 'object_repr')}),
        ('Details', {'fields': ('changes', 'additional_data')}),
        ('Request Info', {'fields': ('ip_address', 'user_agent')}),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
