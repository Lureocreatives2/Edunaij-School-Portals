from base64 import urlsafe_b64encode

from allauth.mfa.adapter import DefaultMFAAdapter
from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.utils.crypto import salted_hmac


class EncryptedMFAAdapter(DefaultMFAAdapter):
    def _cipher(self):
        keys = [settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS]
        return MultiFernet([
            Fernet(urlsafe_b64encode(salted_hmac(
                'edunaij.mfa.encryption', 'authenticator', secret=key, algorithm='sha256',
            ).digest()))
            for key in keys
        ])

    def encrypt(self, text):
        return self._cipher().encrypt(text.encode()).decode('ascii')

    def decrypt(self, encrypted_text):
        return self._cipher().decrypt(encrypted_text.encode('ascii')).decode()
