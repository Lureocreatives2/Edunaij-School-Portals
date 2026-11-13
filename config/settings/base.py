import os
from pathlib import Path

import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from django.core.exceptions import ImproperlyConfigured
from django.contrib.messages import constants as messages

from django_school_management.accounts.constants import AccountURLConstants
from utilities.constants import settings_message_constants


######################## Django Core & Custom Configs ########################
##############################################################################

BASE_DIR = Path(__file__).parent.parent.parent

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, True),
    USE_PAYMENT_OPTIONS=(bool, True),
    USE_SENTRY=(bool, False),
    USE_MAILCHIMP=(bool, False),
    SSL_ISSANDBOX=(bool, True),
    USE_STRIPE=(bool, False),
    IS_DEMO_ENV=(bool, False),
)
# reading .env file
env.read_env(str(BASE_DIR / "envs/.env"))

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')
ADMIN_MFA_REQUIRED = env.bool('ADMIN_MFA_REQUIRED', default=not DEBUG)
MFA_SUPPORTED_TYPES = ['totp', 'recovery_codes']
MFA_TOTP_ISSUER = 'edunaij'
MFA_ADAPTER = 'django_school_management.accounts.mfa_adapter.EncryptedMFAAdapter'
MFA_TRUST_ENABLED = False
SCHOOL_EMAIL_DOMAIN = env('SCHOOL_EMAIL_DOMAIN', default='').strip().lower()

try:
    DJANGO_ADMIN_URL = env('DJANGO_ADMIN_URL')
except ImproperlyConfigured:
    DJANGO_ADMIN_URL = 'admin'

DEFAULT_APPS = [
    'django_school_management.maintenance',
    'django_school_management.audit',
    'axes',
    'auditlog',
    'django_school_management.communications',
    'django_school_management.reports',
    'django_school_management.learning',
    'django_school_management.parents',
    'django_school_management.billing',
    'django_school_management.accounts.apps.AccountsConfig',  # must be on top
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # allauth required
    'django.contrib.sites',
]

LOCAL_APPS = [
    'django_school_management.platform_control',
    'django_school_management.students.apps.StudentsConfig',
    'django_school_management.teachers.apps.TeachersConfig',
    'django_school_management.result.apps.ResultConfig',
    'django_school_management.academics.apps.AcademicsConfig',
    'django_school_management.pages.apps.PagesConfig',
    'django_school_management.articles.apps.ArticlesConfig',
    'django_school_management.institute.apps.InstituteConfig',
    'django_school_management.curriculum.apps.CurriculumConfig',
    'django_school_management.payments.apps.PaymentsConfig',
    'django_school_management.notices.apps.NoticesConfig',
    'django_school_management.tenants.apps.TenantsConfig',
]

# third party apps
THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap4',
    'rolepermissions',
    'taggit',
    'django_extensions',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.mfa',
    'allauth.socialaccount',
    'mptt',
    'widget_tweaks',
    'django_social_share',
    'django_countries',
    'import_export',
    # 'admin_honeypot',   # admin_honeypot doesn't support Django 4
    'django_tables2',
    'bootstrap4',
    'django_file_form',
    'tinymce',
    # API Documentation and Advanced Features
    'drf_yasg',
    'django_rest_passwordreset',
    # Monitoring
    'django_prometheus',
]

INSTALLED_APPS = DEFAULT_APPS + LOCAL_APPS + THIRD_PARTY_APPS

SITE_ID = 1

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
    'django_school_management.tenants.middleware.TenantMiddleware',
    'django_school_management.utils.middleware.AppMetricsMiddleware',
    'axes.middleware.AxesMiddleware',

]

SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # ctx processeor to attach institute data in templates
                "context_processors.attach_resources.attach_institute_data_ctx_processor",
                "context_processors.attach_resources.attach_urls_for_common_templates",
                "context_processors.attach_resources.attach_dashboard_menu_items",
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database (django_prometheus backend for query/connection metrics)
DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': env('DB_NAME', default='db.sqlite3'),
        'USER': env('DB_USER', default=''),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default=''),
        'PORT': env('DB_PORT', default=''),
    }
}

# Cache (django_prometheus backend for hit/miss/fail metrics)
CACHES = {
    'default': {
        'BACKEND': 'django_prometheus.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{env("REDIS_HOST")}:{env("REDIS_PORT")}/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

# Write session to the DB, only load it from the cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# SET MYSQLDB charset for storing Bengali text
if 'mysql' in DATABASES['default']['ENGINE']:
    DATABASES['default']['OPTIONS'] = {'charset': 'utf8mb4'}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']

# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = env('TIME_ZONE')

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_ROOT = str(BASE_DIR / 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    str(BASE_DIR / 'static')
]

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger'
}

MEDIA_ROOT = str(BASE_DIR / 'media')
MEDIA_URL = '/media/'

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_USE_TLS = True

EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')

# login/register redirects

LOGIN_REDIRECT_URL = 'portal_home'
LOGOUT_REDIRECT_URL = 'account_login'

LOGIN_URL = AccountURLConstants.profile_complete
LOGOUT_URL = 'account_logout'


######################## Third Party Configs ########################
#####################################################################

# DRF CONFIGS
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'django_school_management.accounts.security.AdminSafeTokenAuthentication',
        'django_school_management.accounts.security.AdminSafeJWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.openapi.AutoSchema',
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
}

CORS_ALLOW_ALL_ORIGINS = True

# SENTRY - For loggin and monitoring purposes
USE_SENTRY = env('USE_SENTRY')
if USE_SENTRY:
    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        # debug=True will work even if the DEBUG=False in Django.
        debug=True
    )

# django-prometheus - production-ready defaults
# Disable at build time (no DB); enable at runtime for migration gauges.
PROMETHEUS_EXPORT_MIGRATIONS = env.bool('PROMETHEUS_EXPORT_MIGRATIONS', True)
PROMETHEUS_METRIC_NAMESPACE = "school"
# SLO-friendly latency buckets (seconds): p50, p90, p95, p99
PROMETHEUS_LATENCY_BUCKETS = (
    0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0,
    2.5, 5.0, 7.5, 10.0, 25.0, 50.0, 75.0, float("inf"),
)

# for permission management
ROLEPERMISSIONS_MODULE = 'django_school_management.academics.roles'
# ROLEPERMISSIONS_REGISTER_ADMIN = True

CRISPY_TEMPLATE_PACK = 'bootstrap4'

CKEDITOR_UPLOAD_PATH = 'ck-uploads/'
CKEDITOR_IMAGE_BACKEND = 'pillow'
CKEDITOR_ALLOW_NONIMAGE_FILES = False
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'extraPlugins': ['codesnippet', 'markdown'], 'width': '100%',
    },
}

# STOP SENDING EMAIL FOR USER REGISTRATION
ACCOUNT_RATE_LIMITS = {'school_registration': '8/m/ip'}
ACCOUNT_EMAIL_VERIFICATION = 'none'   # use 'mandatory' or 'optional' for respective cases.

# Django taggit.
TAGGIT_CASE_INSENSITIVE = True

# =========================== PAYMENTS ===========================
# BRAINTREE FOR HANDLING PAYMENTS
USE_PAYMENT_OPTIONS = env('USE_PAYMENT_OPTIONS')

if USE_PAYMENT_OPTIONS:
    try:
        # Braintree
        BRAINTREE_MERCHANT_ID = env('BRAINTREE_MERCHANT_ID')
        BRAINTREE_PUBLIC_KEY = env('BRAINTREE_PUBLIC_KEY')
        BRAINTREE_PRIVATE_KEY = env('BRAINTREE_PRIVATE_KEY')

        # SSLCommerz
        STORE_ID = env('STORE_ID')
        STORE_PASS = env('STORE_PASS')
        SSL_ISSANDBOX = env('SSL_ISSANDBOX')
    except ImproperlyConfigured:
        raise ImproperlyConfigured(settings_message_constants.INCORRECT_PAYMENT_GATEWAY_SETUP_MESSAGE)

USE_STRIPE = env('USE_STRIPE')
if USE_STRIPE:
    try:
        STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY')
        STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY')
    except ImproperlyConfigured:
        raise ImproperlyConfigured(settings_message_constants.INCORRECT_STRIPE_SETUP_MESSAGE)

# CELERY BROKER CONFIG
try:
    CELERY_BROKER_URL = env('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
    CELERY_ACCEPT_CONTENT = ['application/json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'Asia/Dhaka'
except ImproperlyConfigured:
    raise ImproperlyConfigured(settings_message_constants.INCORRECT_CELERY_REDIS_SETUP_MESSAGE)

# MAILCHIMP INTEGRATION
USE_MAILCHIMP = env('USE_MAILCHIMP')
if USE_MAILCHIMP:
    MAILCHIMP_API_KEY = env('MAILCHIMP_API_KEY')
    MAILCHIMP_DATA_CENTER = env('MAILCHIMP_DATA_CENTER')
    MAILCHIMP_LIST_ID = env('MAILCHIMP_LIST_ID')

TINYMCE_DEFAULT_CONFIG = {
    "theme": "silver",
    "height": 500,
    "menubar": False,
    "plugins": "advlist,autolink,lists,link,image,charmap,print,preview,anchor,"
    "searchreplace,visualblocks,code,fullscreen,insertdatetime,media,table,paste,"
    "code,help,wordcount",
    "toolbar": "undo redo | formatselect | "
    "bold italic backcolor | alignleft aligncenter "
    "alignright alignjustify | bullist numlist outdent indent | "
    "removeformat | help",
}

IS_DEMO_ENV = env('IS_DEMO_ENV')
DEMO_SUPERUSER_USERNAME = env('DEMO_SUPERUSER_USERNAME')
DEMO_SUPERUSER_EMAIL = env('DEMO_SUPERUSER_EMAIL')
DEMO_SUPERUSER_PASSWORD = env('DEMO_SUPERUSER_PASSWORD')


# ==========================================
# JAZZMIN ADMIN THEME CONFIGURATION
# ==========================================
JAZZMIN_SETTINGS = {
    "site_title": "School Admin",
    "site_header": "Nigerian School Management",
    "site_brand": "EduManage NG",
    "welcome_sign": "Welcome to the School Management System",
    "search_model": ["students.Student", "teachers.Teacher", "accounts.User"],
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Students", "url": "admin:students_student_changelist"},
        {"name": "Teachers", "url": "admin:teachers_teacher_changelist"},
        {"name": "Academics", "url": "admin:academics_academicclass_changelist"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "show_ui_builder": True,
    "changeform_format": "horizontal_tabs",
    "related_modal_active": True,
    "custom_css": None,
    "custom_js": None,
    "user_avatar": None,
    "usermenu_links": [
        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
        {"model": "auth.user"},
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "students.Student": "fas fa-user-graduate",
        "teachers.Teacher": "fas fa-chalkboard-teacher",
        "academics.AcademicClass": "fas fa-school",
        "academics.AcademicTerm": "fas fa-calendar-alt",
        "result.StudentResult": "fas fa-chart-line",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-nav",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-outline-info",
        "warning": "btn-outline-warning",
        "danger": "btn-outline-danger",
        "success": "btn-outline-success",
    },
}



# --- Phase 06: Security Hardening ---
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Note: Uncomment these in production when using HTTPS
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# django-axes configuration (Brute-force protection)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hour lockout
AXES_LOCKOUT_PARAMETERS = ['ip_address']


# --- Phase 06: Performance & Scaling ---
# WhiteNoise configuration for efficient static file serving
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- Phase 06: Monitoring & Logging ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose', # Change to 'json' in production
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django_school_management': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_WEBHOOK_SECRET = env('PAYSTACK_WEBHOOK_SECRET', default='')

ACCOUNT_FORMS = {'signup': 'django_school_management.accounts.signup.SchoolSignupForm'}

PLATFORM_HOSTS = env.list('PLATFORM_HOSTS', default=[])
