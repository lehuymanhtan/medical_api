"""
Utility Serializers (File Upload)
"""
from rest_framework import serializers
from mainAPI.models import UploadedFile
from django.core.validators import FileExtensionValidator
import magic


class ImageUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for image upload
    Validates file type and size
    """
    file = serializers.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Image file (.jpg, .jpeg, .png only)"
    )
    
    class Meta:
        model = UploadedFile
        fields = ['file']
    
    def validate_file(self, value):
        """Validate file size and MIME type"""
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Validate MIME type using python-magic
        mime = magic.from_buffer(value.read(1024), mime=True)
        value.seek(0)  # Reset file pointer
        
        allowed_mimes = ['image/jpeg', 'image/png']
        if mime not in allowed_mimes:
            raise serializers.ValidationError(
                f"Invalid file type. Only JPEG and PNG images are allowed. Detected: {mime}"
            )
        
        return value
    
    def create(self, validated_data):
        """Create uploaded file record with metadata"""
        file_obj = validated_data['file']
        
        # Get MIME type
        mime = magic.from_buffer(file_obj.read(1024), mime=True)
        file_obj.seek(0)
        
        # Create the record
        uploaded_file = UploadedFile.objects.create(
            uploaded_by=self.context['request'].user,
            file=file_obj,
            file_name=file_obj.name,
            file_size=file_obj.size,
            mime_type=mime,
            url=self.context['request'].build_absolute_uri(file_obj.url) if hasattr(file_obj, 'url') else '',
        )
        
        # Set the URL after saving (when we have the file path)
        uploaded_file.url = self.context['request'].build_absolute_uri(uploaded_file.file.url)
        uploaded_file.save()
        
        return uploaded_file
