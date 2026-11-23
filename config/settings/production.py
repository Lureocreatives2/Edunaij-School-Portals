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

# Railway terminates TLS at its edge and supplies the public platform hostname.
if env.bool('RAILWAY_DEPLOYMENT', default=False):
    from pathlib import PurePosixPath
    from django.core.exceptions import ImproperlyConfigured
    from django.http.request import split_domain_port

    railway_host = env('RAILWAY_PUBLIC_DOMAIN', default='').strip().lower()
    if railway_host:
        if split_domain_port(railway_host)[0] != railway_host:
            raise ImproperlyConfigured('RAILWAY_PUBLIC_DOMAIN must be a hostname.')
        ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, railway_host]))
        PLATFORM_HOSTS = list(dict.fromkeys([*PLATFORM_HOSTS, railway_host]))
        CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, 'https://' + railway_host]))
    ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, 'healthcheck.railway.app']))
    PLATFORM_HOSTS = list(dict.fromkeys([*PLATFORM_HOSTS, 'healthcheck.railway.app']))
    DATABASES = {'default': env.db('DATABASE_URL')}
    if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('Railway deployment requires PostgreSQL DATABASE_URL.')
    DATABASES['default']['CONN_MAX_AGE'] = 0
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
    redis_url = env('REDIS_URL', default='').strip()
    if redis_url:
        CACHES['default']['LOCATION'] = redis_url
    else:
        CACHES = {'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'edunaij_cache',
        }}
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_TASK_STORE_EAGER_RESULT = False
    mount = env('RAILWAY_VOLUME_MOUNT_PATH', default='').strip()
    if mount:
        mount_path = PurePosixPath(mount)
        media_path = PurePosixPath(str(MEDIA_ROOT))
        if (not mount_path.is_absolute() or mount_path == PurePosixPath('/')
                or '..' in mount_path.parts or '..' in media_path.parts
                or not media_path.is_relative_to(mount_path)):
            raise ImproperlyConfigured('MEDIA_ROOT must be inside the Railway upload volume.')
        if media_path == mount_path:
            raise ImproperlyConfigured('Use a media subdirectory inside the Railway upload volume.')
    elif not env.bool('ALLOW_EPHEMERAL_MEDIA', default=False):
        raise ImproperlyConfigured('Attach an upload volume, or explicitly enable ALLOW_EPHEMERAL_MEDIA for a demo.')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REDIRECT_EXEMPT = [r'^health/$']
    ADMIN_MFA_REQUIRED = True
    PROMETHEUS_EXPORT_MIGRATIONS = False
    RESEND_API_KEY = env('RESEND_API_KEY', default='')
    if RESEND_API_KEY:
        EMAIL_BACKEND = 'django_school_management.communications.email_backend.ResendBackend'
    else:
        # Do not leak recovery links into deployment logs when email is unconfigured.
        EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

if env.bool('RAILWAY_DEPLOYMENT', default=False):
    # Container logs belong on stdout/stderr, not an unwritable application directory.
    LOGGING['handlers'].pop('file', None)
    LOGGING['root']['handlers'] = ['console']
    for logger in LOGGING['loggers'].values():
        logger['handlers'] = ['console']
