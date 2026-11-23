"""Transactional email over HTTPS for hosts that block outbound SMTP."""
import base64

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            if not message.recipients():
                continue
            try:
                # Apply Django's header injection validation before making a request.
                message.message()
                payload = {'from': message.from_email, 'subject': message.subject}
                for field in ('to', 'cc', 'bcc', 'reply_to'):
                    if getattr(message, field):
                        payload[field] = getattr(message, field)
                payload['html' if message.content_subtype == 'html' else 'text'] = message.body
                for content, mimetype in getattr(message, 'alternatives', []):
                    if mimetype != 'text/html':
                        raise ValueError('Unsupported email alternative.')
                    payload['html'] = content
                if message.extra_headers:
                    payload['headers'] = message.extra_headers
                for attachment in message.attachments:
                    if not isinstance(attachment, tuple) or len(attachment) != 3:
                        raise ValueError('Unsupported email attachment.')
                    filename, content, mimetype = attachment
                    content = content.encode('utf-8') if isinstance(content, str) else content
                    payload.setdefault('attachments', []).append({
                        'filename': filename, 'content_type': mimetype,
                        'content': base64.b64encode(content).decode('ascii'),
                    })
                if not settings.RESEND_API_KEY:
                    raise ValueError('Email provider is not configured.')
                response = requests.post('https://api.resend.com/emails', json=payload,
                    headers={'Authorization': 'Bearer ' + settings.RESEND_API_KEY},
                    timeout=20, allow_redirects=False)
                if not 200 <= response.status_code < 300:
                    raise ValueError('Email provider rejected the request.')
                sent += 1
            except Exception:
                if not self.fail_silently:
                    # Provider responses can contain addresses and sensitive content.
                    raise RuntimeError('Email delivery failed; check provider configuration and delivery logs.') from None
        return sent
