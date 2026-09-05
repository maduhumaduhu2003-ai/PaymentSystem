import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# ============================================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================================
load_dotenv()

# ============================================================================
# BASE DIRECTORY
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SECURITY
# ============================================================================
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-key-change-this")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get(
        "ALLOWED_HOSTS", "localhost,127.0.0.1,.onrender.com"
    ).split(",") if host.strip()
]

# ============================================================================
# APPLICATIONS
# ============================================================================
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third Party
    "crispy_forms",
    "corsheaders",
    "whitenoise",
    
    # Local Apps
    "accounts",
    "packages",
    "payments",
    "business",
]

# ============================================================================
# MIDDLEWARE
# ============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ============================================================================
# URL / WSGI
# ============================================================================
ROOT_URLCONF = "PaymentSystem.urls"
WSGI_APPLICATION = "PaymentSystem.wsgi.application"

# ============================================================================
# TEMPLATES
# ============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ============================================================================
# DATABASE
# ============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Production (Render/PostgreSQL)
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Local (SQLite for development)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC FILES
# ============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ============================================================================
# DEFAULT PRIMARY KEY
# ============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# CUSTOM USER MODEL
# ============================================================================
AUTH_USER_MODEL = "accounts.User"

# ============================================================================
# AUTHENTICATION BACKENDS (ModelBackend tu)
# ============================================================================
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# ============================================================================
# LOGIN / LOGOUT
# ============================================================================
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# ============================================================================
# CORS CONFIGURATION
# ============================================================================
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in os.environ.get(
            "CORS_ALLOWED_ORIGINS",
            "https://satpay.onrender.com,https://*.onrender.com"
        ).split(",") if origin.strip()
    ]

CORS_ALLOW_CREDENTIALS = True

# ============================================================================
# CSRF TRUSTED ORIGINS
# ============================================================================
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "https://satpay.onrender.com,https://*.onrender.com,http://localhost:8000"
    ).split(",") if origin.strip()
]

# ============================================================================
# CLICKPESA CONFIGURATION
# ============================================================================
CLICKPESA_API_KEY = os.environ.get("CLICKPESA_API_KEY")
CLICKPESA_CLIENT_ID = os.environ.get("CLICKPESA_CLIENT_ID")
CLICKPESA_API_SECRET = os.environ.get("CLICKPESA_API_SECRET")
CLICKPESA_BASE_URL = os.environ.get("CLICKPESA_BASE_URL", "https://api.clickpesa.com")
CLICKPESA_CALLBACK_URL = os.environ.get("CLICKPESA_CALLBACK_URL", "https://satpay.onrender.com/payments/callback/")
CLICKPESA_TIMEOUT = 30
CLICKPESA_MAX_RETRIES = 3

# ============================================================================
# SELCOM CONFIGURATION
# ============================================================================
SELCOM_API_KEY = os.environ.get("SELCOM_API_KEY")
SELCOM_API_SECRET = os.environ.get("SELCOM_API_SECRET")
SELCOM_BASE_URL = os.environ.get("SELCOM_BASE_URL", "https://api.selcom.com/v1")

# ============================================================================
# LOGGING
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "payments": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "clickpesa": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ============================================================================
# SECURITY
# ============================================================================
X_FRAME_OPTIONS = "SAMEORIGIN"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 hours
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")