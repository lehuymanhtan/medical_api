"""
Examination Serializers
"""
from rest_framework import serializers
from mainAPI.models import Examination, Appointment, User, Prescription


class PrescriptionSerializer(serializers.ModelSerializer):
    """Read serializer — used for nested display in ExaminationSerializer"""
    class Meta:
        model = Prescription
        fields = ['id', 'name', 'morning', 'evening', 'before_meal', 'quantity', 'summary']
        read_only_fields = ['id']


class PrescriptionCreateSerializer(serializers.ModelSerializer):
    """Write serializer — used by PrescriptionViewSet to create/update prescriptions"""
    class Meta:
        model = Prescription
        fields = ['name', 'morning', 'evening', 'before_meal', 'quantity', 'summary']
        extra_kwargs = {
            'name':        {'help_text': 'Medicine name.'},
            'morning':     {'help_text': 'Take in the morning.'},
            'evening':     {'help_text': 'Take in the evening.'},
            'before_meal': {'help_text': 'Take before meals.'},
            'quantity':    {'help_text': 'Total units dispensed.'},
            'summary':     {'help_text': 'Additional instructions.'},
        }


class ExaminationSummarySerializer(serializers.ModelSerializer):
    """
    Summary serializer for examination list views
    """
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    diagnosis_short = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source='examination_date', read_only=True)
    
    class Meta:
        model = Examination
        fields = [
            'id',
            'date',
            'doctor_name',
            'diagnosis_short',
            'status',
        ]
    
    def get_diagnosis_short(self, obj) -> str:
        """Return truncated diagnosis"""
        if obj.status == Examination.Status.COMPLETED and obj.final_diagnosis:
            return obj.final_diagnosis[:100]
        elif obj.initial_diagnosis:
            return obj.initial_diagnosis[:100]
        return "No diagnosis yet"


class ExaminationSerializer(serializers.ModelSerializer):
    """
    Full examination serializer for detailed views
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    medicines = PrescriptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Examination
        fields = [
            'id',
            'patient',
            'patient_name',
            'doctor',
            'doctor_name',
            'appointment',
            'symptoms',
            'initial_diagnosis',
            'notes',
            'final_diagnosis',
            'blood_pressure',
            'heart_rate',
            'temperature',
            'status',
            'examination_date',
            'finalized_at',
            'created_at',
            'updated_at',
            'medicines',
        ]
        read_only_fields = [
            'id',
            'examination_date',
            'finalized_at',
            'created_at',
            'updated_at',
        ]


class ExaminationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating examinations
    Doctor is automatically set from request.user
    appointment_id is optional (for emergency cases without prior appointment)
    """
    patient_id = serializers.UUIDField(write_only=True)
    appointment_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Examination
        fields = [
            'patient_id',
            'appointment_id',
            'symptoms',
            'initial_diagnosis',
            'notes',
            'blood_pressure',
            'heart_rate',
            'temperature',
        ]
        extra_kwargs = {
            'patient_id': {'help_text': 'UUID of the student/patient.'},
            'appointment_id': {'help_text': 'UUID of the pending appointment to be processed.'},
            'symptoms': {'help_text': 'Detailed description of patient symptoms.'},
            'initial_diagnosis': {'help_text': 'Preliminary diagnosis based on initial check.'},
            'blood_pressure': {'help_text': 'Blood pressure reading (e.g., 120/80).'},
            'heart_rate': {'help_text': 'Heart rate in beats per minute (bpm).'},
            'temperature': {'help_text': 'Body temperature in Celsius (°C).'},
        }
    
    def validate(self, attrs):
        """Validate appointment and patient"""
        patient_id = attrs.pop('patient_id')
        appointment_id = attrs.pop('appointment_id', None)
        
        # Validate patient exists and is a student
        try:
            patient = User.objects.get(id=patient_id, role=User.Role.STUDENT)
            attrs['patient'] = patient
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid patient ID")
        
        # Validate appointment if provided
        if appointment_id:
            try:
                appointment = Appointment.objects.get(id=appointment_id)
                try:
                    _ = appointment.examination
                    raise serializers.ValidationError("This appointment already has an examination")
                except Examination.DoesNotExist:
                    pass
                attrs['appointment'] = appointment
                
                # Validate patient matches appointment
                if appointment.patient != patient:
                    raise serializers.ValidationError("Patient ID doesn't match appointment")
            except Appointment.DoesNotExist:
                raise serializers.ValidationError("Invalid appointment ID")
        else:
            # Emergency case - no appointment
            attrs['appointment'] = None
        
        return attrs
    
    def create(self, validated_data):
        """Set doctor from request context and update appointment status"""
        validated_data['doctor'] = self.context['request'].user
        examination = super().create(validated_data)
        
        # Update appointment status
        if examination.appointment:
            examination.appointment.status = Appointment.Status.COMPLETED
            examination.appointment.save()
        
        return examination


class ExaminationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating draft examinations
    """
    class Meta:
        model = Examination
        fields = [
            'symptoms',
            'initial_diagnosis',
            'notes',
            'blood_pressure',
            'heart_rate',
            'temperature',
        ]
        extra_kwargs = {
            'blood_pressure': {'help_text': 'Update blood pressure reading (e.g., 120/80).'},
            'heart_rate': {'help_text': 'Update heart rate (bpm).'},
            'temperature': {'help_text': 'Update temperature (°C).'},
        }
    
    def validate(self, attrs):
        """Prevent updates to finalized examinations"""
        if self.instance.status == Examination.Status.COMPLETED:
            raise serializers.ValidationError("Cannot update finalized examination")
        return attrs


class ExaminationFinalizeSerializer(serializers.ModelSerializer):
    """
    Serializer for finalizing examinations
    Requires final_diagnosis and prescription
    """
    class Meta:
        model = Examination
        fields = [
            'final_diagnosis',
            'notes',
        ]
        extra_kwargs = {
            'final_diagnosis': {'help_text': 'Conclusive diagnosis (required for finalization).'},
            'notes': {'help_text': 'Final notes or follow-up instructions.'},
        }
    
    def validate(self, attrs):
        """Ensure required fields are present"""
        if not attrs.get('final_diagnosis'):
            raise serializers.ValidationError("Final diagnosis is required for finalization")
        
        if self.instance.status == Examination.Status.COMPLETED:
            raise serializers.ValidationError("Examination is already finalized")
        
        return attrs
    
    def update(self, instance, validated_data):
        """Finalize the examination"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.finalize()
        return instance
