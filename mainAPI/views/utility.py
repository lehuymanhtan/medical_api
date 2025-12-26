"""
Utility Views (File Upload)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from mainAPI.serializers.utility import ImageUploadSerializer


class ImageUploadView(APIView):
    """
    Image upload endpoint
    Supports .jpg, .jpeg, .png only
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
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
