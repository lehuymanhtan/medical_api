from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from mainAPI.models import FCMDeviceToken
from mainAPI.serializers.notification import FCMDeviceTokenSerializer

class FCMDeviceTokenViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    Endpoint for users to register or delete their FCM device tokens
    """
    http_method_names = ['post', 'delete']
    serializer_class = FCMDeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return FCMDeviceToken.objects.filter(user=self.request.user)
        
    @extend_schema(
        tags=['Notifications'],
        summary='Đăng ký Token nhận thông báo',
        description='Gửi token Firebase Cloud Messaging của thiết bị để nhận push notification.'
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
