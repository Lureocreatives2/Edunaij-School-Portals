"""Check Render settings without a live database or provider credentials."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env = dict(os.environ)
env.update({
    'DEBUG': 'False', 'RENDER': 'true',
    'DJANGO_SETTINGS_MODULE': 'config.settings',
    'RENDER_EXTERNAL_HOSTNAME': 'edunaij-check.onrender.com',
    'SECRET_KEY': 'deployment-check-only-' + 'a7B9c5D4e3F2g1H0' * 4,
    'DATABASE_URL': 'postgresql://check:check@127.0.0.1:5432/edunaij',
    'REDIS_URL': 'redis://127.0.0.1:6379/0',
    'MEDIA_ROOT': '/var/data/media',
    'ALLOWED_HOSTS': '', 'CSRF_TRUSTED_ORIGINS': '', 'PLATFORM_HOSTS': '',
    'PROMETHEUS_EXPORT_MIGRATIONS': 'False', 'USE_PAYMENT_OPTIONS': 'False',
})
code = """
import django
django.setup()
from django.conf import settings
assert not settings.DEBUG
assert settings.ADMIN_MFA_REQUIRED
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
assert settings.CACHES['default']['LOCATION'] == 'redis://127.0.0.1:6379/0'
assert 'edunaij-check.onrender.com' in settings.PLATFORM_HOSTS
assert 'edunaij-check.onrender.com' in settings.ALLOWED_HOSTS
assert 'https://edunaij-check.onrender.com' in settings.CSRF_TRUSTED_ORIGINS
assert settings.STORAGES['staticfiles']['BACKEND'].startswith('whitenoise.')
assert settings.MEDIA_ROOT == '/var/data/media'
assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')
print('Render settings verified.')
"""
subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, check=True)
subprocess.run([sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'ERROR'],
               cwd=ROOT, env=env, check=True)
subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'],
               cwd=ROOT, env=env, check=True)

frontend_check = """
from django.core.wsgi import get_wsgi_application
from django.test import Client
from django.conf import settings
application = get_wsgi_application()
client = Client(HTTP_HOST='edunaij-check.onrender.com')
for path in ('/', '/static/edunaij/landing.css', '/static/edunaij/landing.js',
             '/static/vendor/bootstrap/bootstrap.min.css',
             '/static/vendor/bootstrap/bootstrap.bundle.min.js',
             '/static/vendor/fontawesome/css/all.min.css',
             '/static/edunaij/classroom.webp', '/static/edunaij/workspace-preview.webp'):
    response = client.get(path, secure=True)
    assert response.status_code == 200, (path, response.status_code)
    response.close()
print('Production landing page and collected frontend assets verified.')
"""
subprocess.run([sys.executable, '-c', frontend_check], cwd=ROOT, env=env, check=True)
