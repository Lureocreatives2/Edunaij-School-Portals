"""Verify Railway production configuration without provider accounts or a live DB."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
env = dict(os.environ)
env.update({
    'DJANGO_SETTINGS_MODULE': 'config.settings', 'DEBUG': 'False',
    'RAILWAY_DEPLOYMENT': 'True', 'RENDER': 'False',
    'RAILWAY_PUBLIC_DOMAIN': 'edunaij-check.up.railway.app',
    'SECRET_KEY': 'railway-verification-only-' + '5f7X8c9Q4z1M' * 5,
    'DATABASE_URL': 'postgresql://check:check@127.0.0.1:5432/edunaij',
    'REDIS_URL': '', 'RAILWAY_VOLUME_MOUNT_PATH': '',
    'MEDIA_ROOT': '/app/media', 'ALLOW_EPHEMERAL_MEDIA': 'True',
    'ALLOWED_HOSTS': '', 'CSRF_TRUSTED_ORIGINS': '', 'PLATFORM_HOSTS': '',
    'PROMETHEUS_EXPORT_MIGRATIONS': 'False', 'USE_PAYMENT_OPTIONS': 'False',
    'BOOTSTRAP_PLATFORM_OWNER': 'False', 'RESEND_API_KEY': '',
})


def run(code, overrides=None, expected_failure=None):
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT,
        env={**env, **(overrides or {})}, capture_output=True, text=True)
    if expected_failure:
        assert result.returncode != 0 and expected_failure in result.stderr, 'Storage or host guard failed.'
    elif result.returncode:
        raise RuntimeError(result.stderr)
    else:
        print(result.stdout.strip())


setup = 'import django; django.setup(); from django.conf import settings; '
run(setup + """
assert not settings.DEBUG and settings.ADMIN_MFA_REQUIRED
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
assert settings.DATABASES['default']['CONN_MAX_AGE'] == 0
assert settings.CACHES['default']['BACKEND'] == 'django.core.cache.backends.db.DatabaseCache'
assert settings.CELERY_TASK_ALWAYS_EAGER
assert 'edunaij-check.up.railway.app' in settings.PLATFORM_HOSTS
assert 'healthcheck.railway.app' in settings.ALLOWED_HOSTS
assert 'https://edunaij-check.up.railway.app' in settings.CSRF_TRUSTED_ORIGINS
assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')
assert settings.EMAIL_BACKEND == 'django.core.mail.backends.dummy.EmailBackend'
print('Railway production defaults verified.')
""")
run(setup + "assert settings.MEDIA_ROOT == '/data/media'; print('Durable upload configuration verified.')",
    {'RAILWAY_VOLUME_MOUNT_PATH': '/data', 'MEDIA_ROOT': '/data/media', 'ALLOW_EPHEMERAL_MEDIA': 'False'})
run(setup, {'ALLOW_EPHEMERAL_MEDIA': 'False'}, 'Attach an upload volume')
for path in ('/data/../outside', '/other/media', '/data'):
    run(setup, {'RAILWAY_VOLUME_MOUNT_PATH': '/data', 'MEDIA_ROOT': path}, 'ImproperlyConfigured')
run(setup, {'RAILWAY_PUBLIC_DOMAIN': 'https://invalid.example'}, 'must be a hostname')
run(setup, {'DATABASE_URL': 'sqlite:///db.sqlite3'}, 'requires PostgreSQL')
run(setup + """
assert settings.CACHES['default']['LOCATION'] == 'redis://127.0.0.1:6379/1'
assert settings.EMAIL_BACKEND.endswith('ResendBackend')
print('Optional Redis and HTTPS email settings verified.')
""", {'REDIS_URL': 'redis://127.0.0.1:6379/1', 'RESEND_API_KEY': 'test-only-key'})
for command in (['check', '--deploy', '--fail-level', 'ERROR'], ['collectstatic', '--noinput']):
    subprocess.run([sys.executable, 'manage.py', *command], cwd=ROOT, env=env, check=True)
run("""
from django.core.wsgi import get_wsgi_application
from django.test import Client
application = get_wsgi_application()
client = Client(HTTP_HOST='edunaij-check.up.railway.app')
for path in ('/', '/static/edunaij/landing.css', '/static/edunaij/landing.js',
             '/static/vendor/bootstrap/bootstrap.min.css', '/static/vendor/bootstrap/bootstrap.bundle.min.js',
             '/static/edunaij/classroom.webp'):
    response = client.get(path, secure=True)
    assert response.status_code == 200, (path, response.status_code)
    response.close()
print('Railway production landing page and frontend assets verified.')
""")
