"""
User and Patient Profile Serializers
"""
from rest_framework import serializers
from mainAPI.models import User, PatientProfile, DoctorProfile


class LoginRequestSerializer(serializers.Serializer):
    """Serializer for login request"""
    username = serializers.CharField(required=True, help_text="Student ID (e.g., SV001) or Staff Username")
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'}, help_text="User password")


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response"""
    token = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField()
    
    def get_user(self, obj) -> dict:
        return UserProfileSerializer(obj.get('user')).data


class ChangePasswordRequestSerializer(serializers.Serializer):
    """Serializer for change password request"""
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'}, help_text="Mật khẩu cũ")
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'}, help_text="Mật khẩu mới")


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
            'cohort',
            'class_name',
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
    
    age = serializers.SerializerMethodField()
    date_of_birth = serializers.DateField(source='patient_profile.date_of_birth', read_only=True)
    height = serializers.DecimalField(source='patient_profile.height', max_digits=5, decimal_places=2, read_only=True)
    weight = serializers.DecimalField(source='patient_profile.weight', max_digits=5, decimal_places=2, read_only=True)
    fasting_blood_sugar = serializers.DecimalField(source='patient_profile.fasting_blood_sugar', max_digits=5, decimal_places=2, read_only=True)
    hba1c = serializers.DecimalField(source='patient_profile.hba1c', max_digits=5, decimal_places=2, read_only=True)
    red_blood_cells = serializers.DecimalField(source='patient_profile.red_blood_cells', max_digits=5, decimal_places=2, read_only=True)
    hemoglobin = serializers.DecimalField(source='patient_profile.hemoglobin', max_digits=5, decimal_places=2, read_only=True)
    hematocrit = serializers.DecimalField(source='patient_profile.hematocrit', max_digits=5, decimal_places=2, read_only=True)
    white_blood_cells = serializers.DecimalField(source='patient_profile.white_blood_cells', max_digits=5, decimal_places=2, read_only=True)
    platelets = serializers.DecimalField(source='patient_profile.platelets', max_digits=5, decimal_places=2, read_only=True)
    creatinine = serializers.DecimalField(source='patient_profile.creatinine', max_digits=5, decimal_places=2, read_only=True)
    blood_urea_nitrogen = serializers.DecimalField(source='patient_profile.blood_urea_nitrogen', max_digits=5, decimal_places=2, read_only=True)
    ast_sgot = serializers.DecimalField(source='patient_profile.ast_sgot', max_digits=5, decimal_places=2, read_only=True)
    alt_sgpt = serializers.DecimalField(source='patient_profile.alt_sgpt', max_digits=5, decimal_places=2, read_only=True)
    total_bilirubin = serializers.DecimalField(source='patient_profile.total_bilirubin', max_digits=5, decimal_places=2, read_only=True)
    total_cholesterol = serializers.DecimalField(source='patient_profile.total_cholesterol', max_digits=5, decimal_places=2, read_only=True)
    ldl_cholesterol = serializers.DecimalField(source='patient_profile.ldl_cholesterol', max_digits=5, decimal_places=2, read_only=True)
    hdl_cholesterol = serializers.DecimalField(source='patient_profile.hdl_cholesterol', max_digits=5, decimal_places=2, read_only=True)
    triglycerides = serializers.DecimalField(source='patient_profile.triglycerides', max_digits=5, decimal_places=2, read_only=True)
    sodium = serializers.DecimalField(source='patient_profile.sodium', max_digits=5, decimal_places=2, read_only=True)
    potassium = serializers.DecimalField(source='patient_profile.potassium', max_digits=5, decimal_places=2, read_only=True)
    calcium = serializers.DecimalField(source='patient_profile.calcium', max_digits=5, decimal_places=2, read_only=True)
    
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
            'age',
            'date_of_birth',
            'height',
            'weight',
            'fasting_blood_sugar',
            'hba1c',
            'red_blood_cells',
            'hemoglobin',
            'hematocrit',
            'white_blood_cells',
            'platelets',
            'creatinine',
            'blood_urea_nitrogen',
            'ast_sgot',
            'alt_sgpt',
            'total_bilirubin',
            'total_cholesterol',
            'ldl_cholesterol',
            'hdl_cholesterol',
            'triglycerides',
            'sodium',
            'potassium',
            'calcium',
        ]
    
    def get_age(self, obj) -> int:
        from datetime import date
        if hasattr(obj, 'patient_profile') and obj.patient_profile.date_of_birth:
            dob = obj.patient_profile.date_of_birth
            today = date.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return None
    
    def get_allergies(self, obj) -> list:
        """Parse comma-separated allergies into list"""
        if hasattr(obj, 'patient_profile') and obj.patient_profile.allergies:
            return [a.strip() for a in obj.patient_profile.allergies.split(',') if a.strip()]
        return []
    
    def get_last_diagnosis(self, obj) -> str:
        """Get the most recent diagnosis"""
        last_exam = obj.examinations_as_patient.filter(
            status='COMPLETED'
        ).order_by('-examination_date').first()
        
        if last_exam:
            return last_exam.final_diagnosis[:100]  # Truncate to 100 chars
        return None
    
    def get_last_visit_date(self, obj) -> str:
        """Get the date of last examination"""
        last_exam = obj.examinations_as_patient.filter(
            status='COMPLETED'
        ).order_by('-examination_date').first()
        
        if last_exam:
            return last_exam.examination_date.date()
        return None
