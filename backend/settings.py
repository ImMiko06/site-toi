import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-before-production")
DEBUG = env_bool("DEBUG", not env_bool("RENDER", False))

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
ALLOWED_HOSTS.extend(
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if host.strip()
)

CSRF_TRUSTED_ORIGINS = []
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
CSRF_TRUSTED_ORIGINS.extend(
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "backend.wedding",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

USE_WHITENOISE = env_bool("USE_WHITENOISE", not DEBUG)
if USE_WHITENOISE:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend" / "templates"],
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

WSGI_APPLICATION = "backend.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=int(os.environ.get("DATABASE_CONN_MAX_AGE", "600")),
            conn_health_checks=True,
            ssl_require=env_bool("DATABASE_SSL_REQUIRE", True),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Qyzylorda"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

GS_BUCKET_NAME = os.environ.get("GS_BUCKET_NAME", "").strip()
GOOGLE_DRIVE_TOKEN_FILE = os.environ.get("GOOGLE_DRIVE_TOKEN_FILE", str(BASE_DIR / "google-drive-token.json")).strip()
GOOGLE_DRIVE_TOKEN_JSON = os.environ.get("GOOGLE_DRIVE_TOKEN_JSON", "").strip()
GOOGLE_DRIVE_STORAGE = env_bool("GOOGLE_DRIVE_STORAGE", Path(GOOGLE_DRIVE_TOKEN_FILE).exists() or bool(GOOGLE_DRIVE_TOKEN_JSON))
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "13HHHHfLsKXHrOxUcxLSk7YVTA94b-EEs").strip()
GOOGLE_DRIVE_PUBLIC = env_bool("GOOGLE_DRIVE_PUBLIC", True)
GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES = env_bool("GOOGLE_DRIVE_SUPPORTS_ALL_DRIVES", True)
GOOGLE_DRIVE_OAUTH_CLIENT_SECRETS = os.environ.get("GOOGLE_DRIVE_OAUTH_CLIENT_SECRETS", "").strip()
GOOGLE_DRIVE_TIMEOUT_SECONDS = int(os.environ.get("GOOGLE_DRIVE_TIMEOUT_SECONDS", "300"))
GOOGLE_DRIVE_UPLOAD_RETRIES = int(os.environ.get("GOOGLE_DRIVE_UPLOAD_RETRIES", "3"))
GOOGLE_DRIVE_UPLOAD_CHUNK_SIZE = int(os.environ.get("GOOGLE_DRIVE_UPLOAD_CHUNK_SIZE", str(1024 * 1024)))
USE_GOOGLE_DRIVE_MEDIA = GOOGLE_DRIVE_STORAGE and bool(GOOGLE_DRIVE_FOLDER_ID)
USE_GCS_MEDIA = bool(GS_BUCKET_NAME) and not USE_GOOGLE_DRIVE_MEDIA

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if USE_WHITENOISE:
    STORAGES["staticfiles"] = {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }

if USE_GCS_MEDIA:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_BUCKET_NAME,
            "project_id": os.environ.get("GS_PROJECT_ID") or None,
            "location": os.environ.get("GS_LOCATION", "media").strip("/"),
            "file_overwrite": False,
            "default_acl": os.environ.get("GS_DEFAULT_ACL") or None,
            "querystring_auth": env_bool("GS_QUERYSTRING_AUTH", True),
        },
    }

if USE_GOOGLE_DRIVE_MEDIA:
    STORAGES["default"] = {
        "BACKEND": "backend.wedding.drive_storage.GoogleDriveStorage",
        "OPTIONS": {
            "folder_id": GOOGLE_DRIVE_FOLDER_ID,
            "public": GOOGLE_DRIVE_PUBLIC,
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "wedding:gatekeeper"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
