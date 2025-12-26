"""
Ticket and TicketReply Serializers
"""
from rest_framework import serializers
from mainAPI.models import Ticket, TicketReply


class TicketReplySerializer(serializers.ModelSerializer):
    """
    Serializer for ticket replies
    """
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    
    class Meta:
        model = TicketReply
        fields = [
            'id',
            'author_name',
            'content',
            'is_staff_reply',
            'attachment_url',
            'created_at',
        ]
        read_only_fields = ['id', 'is_staff_reply', 'created_at']


class TicketSerializer(serializers.ModelSerializer):
    """
    Basic ticket serializer for list views
    """
    creator_name = serializers.CharField(source='creator.full_name', read_only=True)
    last_reply = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id',
            'subject',
            'status',
            'creator_name',
            'related_appointment',
            'created_at',
            'last_reply',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_last_reply(self, obj):
        """Get the content of the most recent reply"""
        last_reply = obj.replies.order_by('-created_at').first()
        if last_reply:
            return last_reply.content[:100]  # Truncate
        return None


class TicketDetailSerializer(serializers.ModelSerializer):
    """
    Detailed ticket serializer including all replies
    """
    creator_name = serializers.CharField(source='creator.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True)
    replies = TicketReplySerializer(many=True, read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id',
            'subject',
            'status',
            'creator_name',
            'assigned_to',
            'assigned_to_name',
            'related_appointment',
            'created_at',
            'updated_at',
            'resolved_at',
            'last_reply_at',
            'replies',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'resolved_at',
            'last_reply_at',
        ]


class TicketCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating tickets with initial reply
    """
    content = serializers.CharField(write_only=True, help_text="Initial message content")
    
    class Meta:
        model = Ticket
        fields = [
            'subject',
            'content',
            'related_appointment',
        ]
    
    def create(self, validated_data):
        """Create ticket and initial reply"""
        content = validated_data.pop('content')
        validated_data['creator'] = self.context['request'].user
        
        ticket = super().create(validated_data)
        
        # Create initial reply
        TicketReply.objects.create(
            ticket=ticket,
            author=ticket.creator,
            content=content,
        )
        
        return ticket


class TicketReplyCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for adding replies to existing tickets
    """
    class Meta:
        model = TicketReply
        fields = [
            'content',
            'attachment_url',
        ]
    
    def create(self, validated_data):
        """Add author from request context"""
        validated_data['author'] = self.context['request'].user
        validated_data['ticket'] = self.context['ticket']
        return super().create(validated_data)
