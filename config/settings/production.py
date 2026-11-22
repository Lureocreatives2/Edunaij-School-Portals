from .base import *
from .base import env


DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

DEFAULT_APPS.insert(0, 'whitenoise.runserver_nostatic')
INSTALLED_APPS = DEFAULT_APPS + LOCAL_APPS + THIRD_PARTY_APPS

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# HTTPS is required for production sessions and CSRF cookies.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# Render terminates HTTPS at its trusted edge proxy.
if env.bool('RENDER', default=False):
    from django.core.exceptions import ImproperlyConfigured
    from django.http.request import split_domain_port

    render_host = env('RENDER_EXTERNAL_HOSTNAME', default='').strip().lower()
    if render_host:
        if split_domain_port(render_host)[0] != render_host:
            raise ImproperlyConfigured('RENDER_EXTERNAL_HOSTNAME must be a hostname.')
        ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, render_host]))
        PLATFORM_HOSTS = list(dict.fromkeys([*PLATFORM_HOSTS, render_host]))
        CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, 'https://' + render_host]))
    DATABASES = {'default': env.db('DATABASE_URL')}
    if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('Render deployment requires PostgreSQL DATABASE_URL.')
    DATABASES['default']['CONN_MAX_AGE'] = 60
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
    CACHES['default']['LOCATION'] = env('REDIS_URL')
    CELERY_BROKER_URL = env('REDIS_URL')
    CELERY_RESULT_BACKEND = env('REDIS_URL')
    # Initial single-service deployment runs tasks in the web process.
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    if not env('MEDIA_ROOT', default='').startswith('/var/data/'):
        raise ImproperlyConfigured('Set MEDIA_ROOT below the persistent /var/data disk.')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REDIRECT_EXEMPT = [r'^health/$']
    ADMIN_MFA_REQUIRED = True
    PROMETHEUS_EXPORT_MIGRATIONS = False
