from .settings import *

# Development profile overrides
DEBUG = True

# Allow everything in dev (behind local network)
ALLOWED_HOSTS = ["*"]

# Trusted origins for CSRF in dev
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Email to console in dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Static files served by Django in dev
STATIC_URL = 'static/'

# Security relaxations for dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Mark environment
WAF_ENV = 'dev'

# Console logging for WAF/Proxy middleware
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        # WAF request phase logs
        'waf.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django request logs (helpful for status codes)
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
