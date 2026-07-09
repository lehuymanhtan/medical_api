import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    Safe to call multiple times.
    """
    if not firebase_admin._apps:
        try:
            cred_base64 = getattr(settings, 'FIREBASE_CREDENTIALS_BASE64', '')
            cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
            
            if cred_base64:
                import base64
                import json
                cred_dict = json.loads(base64.b64decode(cred_base64).decode('utf-8'))
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully from Base64 env var.")
            elif cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully from file path.")
            else:
                logger.warning(f"Firebase credentials not found (no Base64 env or valid path). Notifications will be mocked.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")

def send_fcm_notification(user, title, body, data=None):
    """
    Send push notification to all devices registered by the user.
    """
    # Auto-initialize if not done
    initialize_firebase()
    
    tokens = user.fcm_tokens.values_list('token', flat=True)
    if not tokens:
        logger.info(f"User {user.email} has no registered FCM tokens.")
        return 0
        
    if not firebase_admin._apps:
        # Mocking notification if firebase not initialized
        logger.info(f"[MOCK NOTIFICATION to {user.email}]: {title} - {body}")
        return len(tokens)
        
    # Send multicast message to all devices
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=list(tokens),
    )
    
    try:
        response = messaging.send_multicast(message)
        logger.info(f"Successfully sent {response.success_count} messages to {user.email}.")
        
        # Clean up invalid tokens
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # The order of responses corresponds to the order of tokens
                    failed_tokens.append(list(tokens)[idx])
            
            if failed_tokens:
                user.fcm_tokens.filter(token__in=failed_tokens).delete()
                logger.info(f"Deleted {len(failed_tokens)} invalid tokens for {user.email}.")
                
        return response.success_count
    except Exception as e:
        logger.error(f"Error sending FCM notification to {user.email}: {e}")
        return 0
