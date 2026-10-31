import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

env = os.environ.get
DEBUG = env("DEBUG", "0") == "1"
SECRET_KEY = env("SECRET_KEY", "")
if not SECRET_KEY:
    raise ValueError("Set SECRET_KEY in the backend environment.")
if not DEBUG and SECRET_KEY == "change-me":
    raise ValueError("Set a unique SECRET_KEY before running with DEBUG disabled.")

ALLOWED_HOSTS = [host.strip() for host in env("ALLOWED_HOSTS", "tuvacomputers.pythonanywhere.com,localhost,127.0.0.1").split(",") if host.strip()]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "shop",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]
database_engine = env("DB_ENGINE", "django.db.backends.sqlite3")
database_name = env("DB_NAME", "") or ("" if "postgresql" in database_engine else str(BASE_DIR / "db.sqlite3"))
if "postgresql" in database_engine and not database_name:
    raise ValueError("Set DB_NAME when using PostgreSQL.")
DATABASES = {"default": {
    "ENGINE": database_engine,
    "NAME": database_name,
    "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60" if "postgresql" in database_engine else "0")),
}}
if "postgresql" in database_engine:
    DATABASES["default"].update({
        "USER": env("DB_USER", ""),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
    })
STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", "") or BASE_DIR / "staticfiles")
MEDIA_URL = env("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", "") or BASE_DIR / "media")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in env("CORS_ALLOWED_ORIGINS", env("FRONTEND_URL", "https://tuvacomputers.netlify.app,http://localhost:5173")).split(",")
    if origin.strip()
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "300/min",
        "assistant": "20/min",
        "alerts": "5/hour",
        "admin_login": "5/min",
        "account_register": "5/hour",
        "account_login": "10/hour",
    },
}
cache_url = env("CACHE_URL", "")
if cache_url:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": cache_url}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "tuva-cache"}}

CELERY_BROKER_URL = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if env("EMAIL_HOST_USER")
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = f"TUVA <{EMAIL_HOST_USER or 'no-reply@tuva.local'}>"
FRONTEND_URL = env("FRONTEND_URL", "https://tuvacomputers.netlify.app,http://localhost:5173")

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT", "1") == "1"
