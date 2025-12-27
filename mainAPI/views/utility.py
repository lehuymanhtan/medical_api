"""
Utility Views (File Upload)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiExample
from mainAPI.serializers.utility import ImageUploadSerializer


class ImageUploadView(APIView):
    """
    Image upload endpoint
    Supports .jpg, .jpeg, .png only
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        tags=['Utilities'],
        operation_id='uploadImage',
        summary='Upload ảnh lên hệ thống',
        description='''Upload file ảnh và nhận lại URL. Chỉ hỗ trợ định dạng .jpg, .jpeg, .png (tối đa 10MB).
Dùng cho hồ sơ hoặc đính kèm ticket.''',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'File ảnh cần upload (jpg, jpeg, png - tối đa 10MB)'
                    }
                }
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'url': {
                        'type': 'string',
                        'example': 'https://cdn.hospital.edu.vn/uploads/img_12345.jpg',
                        'description': 'Đường dẫn truy cập ảnh đã upload'
                    }
                }
            }
        }
    )
    def post(self, request):
        """
        POST /upload/image
        Upload an image file
        """
        serializer = ImageUploadSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            uploaded_file = serializer.save()
            
            return Response(
                {'url': uploaded_file.url},
                status=status.HTTP_200_OK
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
