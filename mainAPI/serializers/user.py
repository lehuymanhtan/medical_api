"""
User and Patient Profile Serializers
"""
from rest_framework import serializers
from mainAPI.models import User, PatientProfile, DoctorProfile, Examination


class ProfileCharField(serializers.CharField):
    def __init__(self, profile_attr, **kwargs):
        self.profile_attr = profile_attr
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        try:
            profile = instance.patient_profile
        except PatientProfile.DoesNotExist:
            return None
        return getattr(profile, self.profile_attr, None)


class ProfileDecimalField(serializers.DecimalField):
    def __init__(self, profile_attr, **kwargs):
        self.profile_attr = profile_attr
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        try:
            profile = instance.patient_profile
        except PatientProfile.DoesNotExist:
            return None
        return getattr(profile, self.profile_attr, None)


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
            'date_of_birth',
            'sex',
            'address',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'role', 'student_id', 'email', 'phone_number']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        email_value = data.get('email')
        if email_value and email_value.endswith('@placeholder.local'):
            data['email'] = ''
        return data


class PatientSummarySerializer(serializers.ModelSerializer):
    """
    Medical summary for patients
    Includes patient profile data
    """
    blood_type = ProfileCharField(profile_attr='blood_type', read_only=True)
    allergies = serializers.SerializerMethodField()
    last_diagnosis = serializers.SerializerMethodField()
    last_visit_date = serializers.SerializerMethodField()
    
    age = serializers.SerializerMethodField()
    date_of_birth = serializers.DateField(read_only=True)
    height = ProfileDecimalField(profile_attr='height', max_digits=5, decimal_places=2, read_only=True)
    weight = ProfileDecimalField(profile_attr='weight', max_digits=5, decimal_places=2, read_only=True)
    fasting_blood_sugar = ProfileDecimalField(profile_attr='fasting_blood_sugar', max_digits=5, decimal_places=2, read_only=True)
    hba1c = ProfileDecimalField(profile_attr='hba1c', max_digits=5, decimal_places=2, read_only=True)
    red_blood_cells = ProfileDecimalField(profile_attr='red_blood_cells', max_digits=5, decimal_places=2, read_only=True)
    hemoglobin = ProfileDecimalField(profile_attr='hemoglobin', max_digits=5, decimal_places=2, read_only=True)
    hematocrit = ProfileDecimalField(profile_attr='hematocrit', max_digits=5, decimal_places=2, read_only=True)
    white_blood_cells = ProfileDecimalField(profile_attr='white_blood_cells', max_digits=5, decimal_places=2, read_only=True)
    platelets = ProfileDecimalField(profile_attr='platelets', max_digits=5, decimal_places=2, read_only=True)
    creatinine = ProfileDecimalField(profile_attr='creatinine', max_digits=5, decimal_places=2, read_only=True)
    blood_urea_nitrogen = ProfileDecimalField(profile_attr='blood_urea_nitrogen', max_digits=5, decimal_places=2, read_only=True)
    ast_sgot = ProfileDecimalField(profile_attr='ast_sgot', max_digits=5, decimal_places=2, read_only=True)
    alt_sgpt = ProfileDecimalField(profile_attr='alt_sgpt', max_digits=5, decimal_places=2, read_only=True)
    total_bilirubin = ProfileDecimalField(profile_attr='total_bilirubin', max_digits=5, decimal_places=2, read_only=True)
    total_cholesterol = ProfileDecimalField(profile_attr='total_cholesterol', max_digits=5, decimal_places=2, read_only=True)
    ldl_cholesterol = ProfileDecimalField(profile_attr='ldl_cholesterol', max_digits=5, decimal_places=2, read_only=True)
    hdl_cholesterol = ProfileDecimalField(profile_attr='hdl_cholesterol', max_digits=5, decimal_places=2, read_only=True)
    triglycerides = ProfileDecimalField(profile_attr='triglycerides', max_digits=5, decimal_places=2, read_only=True)
    sodium = ProfileDecimalField(profile_attr='sodium', max_digits=5, decimal_places=2, read_only=True)
    potassium = ProfileDecimalField(profile_attr='potassium', max_digits=5, decimal_places=2, read_only=True)
    calcium = ProfileDecimalField(profile_attr='calcium', max_digits=5, decimal_places=2, read_only=True)
    
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
        if obj.date_of_birth:
            dob = obj.date_of_birth
            today = date.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return None
    
    def get_allergies(self, obj) -> list:
        try:
            profile = obj.patient_profile
        except PatientProfile.DoesNotExist:
            return []
        return profile.allergies or []
    
    def _get_last_exam(self, obj):
        if not hasattr(obj, '_last_exam_cached'):
            obj._last_exam_cached = obj.examinations_as_patient.filter(
                status=Examination.Status.COMPLETED
            ).order_by('-examination_date').first()
        return obj._last_exam_cached

    def get_last_diagnosis(self, obj) -> str:
        """Get the most recent diagnosis"""
        last_exam = self._get_last_exam(obj)
        
        if last_exam:
            return last_exam.final_diagnosis[:100]  # Truncate to 100 chars
        return None
    
    def get_last_visit_date(self, obj) -> str:
        """Get the date of last examination"""
        last_exam = self._get_last_exam(obj)
        
        if last_exam:
            return last_exam.examination_date.date()
        return None


class MedicalSummaryUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a patient's medical summary fields.
    """
    class Meta:
        model = PatientProfile
        fields = [
            'blood_type', 'allergies', 'height', 'weight', 'fasting_blood_sugar', 'hba1c', 
            'red_blood_cells', 'hemoglobin', 'hematocrit', 'white_blood_cells', 
            'platelets', 'creatinine', 'blood_urea_nitrogen', 'ast_sgot', 
            'alt_sgpt', 'total_bilirubin', 'total_cholesterol', 'ldl_cholesterol', 
            'hdl_cholesterol', 'triglycerides', 'sodium', 'potassium', 'calcium'
        ]

    def validate_allergies(self, value):
        if value is None:
            return value
        if isinstance(value, list):
            return [str(a).strip() for a in value if str(a).strip()]
        return [str(value)]

    def to_internal_value(self, data):
        # Convert empty strings to None for Decimal/Numeric fields
        mutable_data = data.copy() if hasattr(data, 'copy') else data
        for key, value in mutable_data.items():
            if value == "" and key != 'blood_type':
                mutable_data[key] = None
        return super().to_internal_value(mutable_data)


class CreateAccountSerializer(serializers.Serializer):
    """
    Serializer for admin to create a new user account.
    Accepts: username, name, cohort, class_name, password.
    Optional: date_of_birth, sex, address, email, phone_number, role.
    """
    username = serializers.CharField(required=True, help_text="Django username (used for login)")
    name = serializers.CharField(required=True, help_text="Full name of the user")
    cohort = serializers.CharField(required=False, default='', allow_blank=True)
    class_name = serializers.CharField(required=False, default='', allow_blank=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    phone_number = serializers.CharField(required=False, default='', allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True, default=None)
    sex = serializers.ChoiceField(choices=User.Sex.choices, required=False, allow_blank=True, default='')
    address = serializers.CharField(required=False, allow_blank=True, default='', style={'base_template': 'textarea.html'})
    role = serializers.ChoiceField(choices=User.Role.choices, required=False, default=User.Role.STUDENT)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(f"Username '{value}' already exists.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(f"Email '{value}' is already in use.")
        return value

    def create(self, validated_data):
        username = validated_data['username']
        email = validated_data.get('email') or f"{username}@placeholder.local"
        role = validated_data.get('role', User.Role.STUDENT)

        user = User(
            username=username,
            full_name=validated_data['name'],
            cohort=validated_data.get('cohort', ''),
            class_name=validated_data.get('class_name', ''),
            email=email,
            phone_number=validated_data.get('phone_number', ''),
            date_of_birth=validated_data.get('date_of_birth'),
            sex=validated_data.get('sex', ''),
            address=validated_data.get('address', ''),
            role=role,
            student_id=username if role == User.Role.STUDENT else None,
        )
        user.set_password(validated_data['password'])
        user.save()

        # Auto-create PatientProfile for students
        if role == User.Role.STUDENT:
            PatientProfile.objects.get_or_create(user=user)

        return user


class BatchCreateAccountSerializer(serializers.Serializer):
    """
    Serializer for batch account creation.
    Accepts a list of CreateAccountSerializer-compatible objects.
    """
    accounts = CreateAccountSerializer(many=True)

    def validate_accounts(self, value):
        if not value:
            raise serializers.ValidationError("At least one account must be provided.")
        return value

    def create(self, validated_data):
        created_users = []
        for account_data in validated_data['accounts']:
            user = CreateAccountSerializer().create(account_data)
            created_users.append(user)
        return created_users
