from rest_framework import serializers
from mainAPI.models import QueueEntry
from mainAPI.serializers.user import UserProfileSerializer

class QueueEntrySerializer(serializers.ModelSerializer):
    patient_details = serializers.SerializerMethodField()
    
    class Meta:
        model = QueueEntry
        fields = ['id', 'patient', 'patient_details', 'date', 'number', 'status', 'created_at']
        read_only_fields = ['id', 'date', 'number', 'created_at']
        
    def get_patient_details(self, obj):
        # We can just return the full name and student id
        return {
            'full_name': obj.patient.full_name,
            'student_id': obj.patient.student_id,
        }

class QueueEntryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueEntry
        fields = ['id'] # We don't need any input fields to take a number, patient is drawn from request, date is today, number is auto-gen

class QueueEntryStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueEntry
        fields = ['status']
