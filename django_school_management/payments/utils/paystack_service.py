import requests
import hmac
import hashlib
import logging
import re
from django.conf import settings

logger = logging.getLogger(__name__)

class PaystackService:
    BASE_URL = "https://api.paystack.co"
    
    @classmethod
    def get_secret_key(cls):
        return getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        
    @classmethod
    def get_public_key(cls):
        return getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')

    @classmethod
    def initialize_transaction(cls, email, amount, reference, metadata=None):
        """Initialize a Paystack transaction. Amount must be in Kobo (NGN * 100)."""
        headers = {
            "Authorization": f"Bearer {cls.get_secret_key()}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "amount": int(amount * 100), # Convert NGN to Kobo
            "reference": reference,
            "currency": "NGN",
            "metadata": metadata or {}
        }
        try:
            response = requests.post(f"{cls.BASE_URL}/transaction/initialize", json=payload, headers=headers, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Paystack initialization error: {e}")
            return {"status": False, "message": str(e)}

    @classmethod
    def verify_transaction(cls, reference):
        """Verify a Paystack transaction."""
        headers = {
            "Authorization": f"Bearer {cls.get_secret_key()}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(f"{cls.BASE_URL}/transaction/verify/{reference}", headers=headers, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Paystack verification error: {e}")
            return {"status": False, "message": str(e)}

    @classmethod
    def verify_webhook_signature(cls, payload_bytes, signature='', timestamped_header=None):
        # https://paystack.com/docs/payments/webhooks/
        if timestamped_header is not None:
            import time
            parts = [part.strip().partition('=') for part in timestamped_header.split(',')]
            timestamps = [value for key, _, value in parts if key == 't']
            if len(timestamps) != 1 or not re.fullmatch(r'[0-9]{1,12}', timestamps[0]):
                return False
            timestamp = timestamps[0]
            if abs(time.time() - int(timestamp)) > 300:
                return False
            secret = getattr(settings, 'PAYSTACK_WEBHOOK_SECRET', '')
            if not secret:
                return False
            payload = timestamp.encode() + b'.' + payload_bytes
            expected = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()
            return any(re.fullmatch(r'[0-9a-f]{128}', value.partition(':')[2]) and
                hmac.compare_digest(expected, value.partition(':')[2])
                for key, _, value in parts if key == 'v1')
        secret = cls.get_secret_key()
        if not secret or not isinstance(signature, str) or not re.fullmatch(r'[0-9a-f]{128}', signature):
            return False
        expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)
