"""
User and Patient Profile Serializers
"""
from rest_framework import serializers
from mainAPI.models import User, PatientProfile, DoctorProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data
    Includes UUID for QR code generation
    """
    class Meta:
        model = User
        fields = [
            'id',
            'full_name',
            'role',
            'student_id',
            'email',
            'phone_number',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PatientSummarySerializer(serializers.ModelSerializer):
    """
    Medical summary for patients
    Includes patient profile data
    """
    blood_type = serializers.CharField(source='patient_profile.blood_type', read_only=True)
    allergies = serializers.SerializerMethodField()
    last_diagnosis = serializers.SerializerMethodField()
    last_visit_date = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'full_name',
            'student_id',
            'blood_type',
            'allergies',
            'last_diagnosis',
            'last_visit_date',
        ]
    
    def get_allergies(self, obj):
        """Parse comma-separated allergies into list"""
        if hasattr(obj, 'patient_profile') and obj.patient_profile.allergies:
            return [a.strip() for a in obj.patient_profile.allergies.split(',') if a.strip()]
        return []
    
    def get_last_diagnosis(self, obj):
        """Get the most recent diagnosis"""
        last_exam = obj.examinations_as_patient.filter(
            status='COMPLETED'
        ).order_by('-examination_date').first()
        
        if last_exam:
            return last_exam.final_diagnosis[:100]  # Truncate to 100 chars
        return None
    
    def get_last_visit_date(self, obj):
        """Get the date of last examination"""
        last_exam = obj.examinations_as_patient.filter(
            status='COMPLETED'
        ).order_by('-examination_date').first()
        
        if last_exam:
            return last_exam.examination_date.date()
        return None
