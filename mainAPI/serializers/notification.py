from rest_framework import serializers
from mainAPI.models import FCMDeviceToken

class FCMDeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDeviceToken
        fields = ['token']
        
    def create(self, validated_data):
        user = self.context['request'].user
        token, created = FCMDeviceToken.objects.get_or_create(
            user=user,
            token=validated_data['token']
        )
        return token
