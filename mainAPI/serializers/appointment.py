"""
Appointment Serializers
"""
from rest_framework import serializers
from mainAPI.models import Appointment
from datetime import date


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Full appointment serializer for list/retrieve operations
    """
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient_id',
            'patient_name',
            'appointment_date',
            'status',
            'reason',
            'cancellation_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating appointments
    Patient is automatically set from request.user
    """
    class Meta:
        model = Appointment
        fields = [
            'appointment_date',
            'reason',
        ]
        extra_kwargs = {
            'appointment_date': {'help_text': 'Date of the appointment (YYYY-MM-DD). Must be in the future.'},
            'reason': {'help_text': 'Brief reason for the visit or symptoms description.'},
        }
    
    def validate_appointment_date(self, value):
        """Validate appointment date is not in the past"""
        if value < date.today():
            raise serializers.ValidationError("Appointment date cannot be in the past")
        return value
    
    def create(self, validated_data):
        """Automatically set patient from request context"""
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class AppointmentPatchSerializer(serializers.ModelSerializer):
    """
    Serializer for updating appointments (cancel/reschedule)
    """
    new_appointment_date = serializers.DateField(required=False, allow_null=True)
    
    class Meta:
        model = Appointment
        fields = [
            'status',
            'new_appointment_date',
            'cancellation_reason',
        ]
        extra_kwargs = {
            'status': {'help_text': 'New status for the appointment (e.g., CANCELLED).'},
            'new_appointment_date': {'help_text': 'New date if rescheduling (YYYY-MM-DD).'},
            'cancellation_reason': {'help_text': 'Reason for cancellation (required if status is CANCELLED).'},
        }
    
    def validate(self, attrs):
        """Validate status transitions"""
        instance = self.instance
        new_status = attrs.get('status', instance.status)
        
        # Can't modify completed appointments
        if instance.status == Appointment.Status.COMPLETED:
            raise serializers.ValidationError("Cannot modify completed appointments")

        if instance.status == Appointment.Status.CANCELLED:
            raise serializers.ValidationError("Cannot modify a cancelled appointment")
        
        # Validate cancellation
        if new_status == Appointment.Status.CANCELLED and not attrs.get('cancellation_reason'):
            raise serializers.ValidationError("Cancellation reason is required")
        
        # Validate rescheduling
        if 'new_appointment_date' in attrs and attrs['new_appointment_date']:
            if attrs['new_appointment_date'] < date.today():
                raise serializers.ValidationError("New appointment date cannot be in the past")
        
        return attrs
    
    def update(self, instance, validated_data):
        """Handle rescheduling logic"""
        new_date = validated_data.pop('new_appointment_date', None)
        
        if new_date:
            instance.appointment_date = new_date
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
