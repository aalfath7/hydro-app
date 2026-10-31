import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(nama: str, bawaan: bool = False) -> bool:
    return os.environ.get(nama, str(bawaan)).lower() in {"1", "true", "yes"}


def env_list(nama: str) -> list[str]:
    return [v.strip() for v in os.environ.get(nama, "").split(",") if v.strip()]


DEBUG = env_bool("DJANGO_DEBUG")

if DEBUG:
    SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-tidak-untuk-produksi")
else:
    # Sengaja gagal saat start kalau secret belum diisi.
    SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS") or (["localhost", "127.0.0.1"] if DEBUG else [])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.headless",
    "auditlog",
    "axes",
    "inti",
    "akun",
    "produk",
    "stok",
    "pembelian",
    "laporan",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "hydro"),
        "USER": os.environ.get("POSTGRES_USER", "hydro"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "hydro"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5433"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "akun.Pengguna"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
MEDIA_URL = "/media/"

# Login: akun hanya dibuat pemilik, tanpa email, dan sesi lewat cookie.
ACCOUNT_ADAPTER = "akun.adapter.AdapterAkun"
ACCOUNT_LOGIN_METHODS = {"username"}
ACCOUNT_SIGNUP_FIELDS = ["username*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]
MFA_ALLOW_UNVERIFIED_EMAIL = True
MFA_TOTP_ISSUER = "Hydro"

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_CLIENT_IP_CALLABLE = "akun.adapter.ip_klien"
AXES_USERNAME_CALLABLE = "akun.adapter.username_axes"
AXES_ENABLED = env_bool("AXES_ENABLED", True)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 12
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", True)
    # Healthcheck container memanggil Django langsung lewat HTTP.
    SECURE_REDIRECT_EXEMPT = [r"^api/kesehatan/$"]
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["inti.autentikasi.AutentikasiSesi"],
    "DEFAULT_PERMISSION_CLASSES": ["inti.izin.PunyaIzin"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "inti.paginasi.Paginasi",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "inti.galat.penangan_galat",
    "URL_FORMAT_OVERRIDE": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Hydro API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "MetodeBayarEnum": "pembelian.models.MetodeBayar",
        "JenisMutasiEnum": "stok.models.JenisMutasi",
        "StatusOpnameEnum": "stok.models.StatusOpname",
        "StatusTransaksiEnum": "pembelian.models.StatusTransaksi",
    },
}

FOTO_MAKS_BYTE = 2 * 1024 * 1024
IMPOR_MAKS_BYTE = 5 * 1024 * 1024
HARI_HAMPIR_KEDALUWARSA = int(os.environ.get("HARI_HAMPIR_KEDALUWARSA", "60"))
NAMA_PERUSAHAAN = os.environ.get("NAMA_PERUSAHAAN", "Air Minum Kemasan")
ALAMAT_PERUSAHAAN = os.environ.get("ALAMAT_PERUSAHAAN", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
