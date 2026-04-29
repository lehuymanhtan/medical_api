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
        self._detected_mime = mime
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
        mime = getattr(self, '_detected_mime', None)
        if not mime:
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
        # Set the URL after saving
        file_url = uploaded_file.file.url
        request = self.context['request']
        
        # Check if URL is already absolute (e.g. S3)
        if file_url.startswith(('http:', 'https:')):
            uploaded_file.url = file_url
        else:
            # Handle local storage with proxy headers
            x_forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
            if x_forwarded_host:
                x_forwarded_proto = request.META.get('HTTP_X_FORWARDED_PROTO', request.scheme)
                uploaded_file.url = f"{x_forwarded_proto}://{x_forwarded_host}{file_url}"
            else:
                uploaded_file.url = request.build_absolute_uri(file_url)
        
        uploaded_file.save(update_fields=['url'])
        
        return uploaded_file
