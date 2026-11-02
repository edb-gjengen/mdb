import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Off unless DJANGO_DEBUG says otherwise; mise.toml turns it on for development.
DEBUG = os.getenv("DJANGO_DEBUG", "").lower() in ("1", "true", "yes")

ADMINS = ("sysadmin@example.com",)

MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    }
}
TIME_ZONE = "Europe/Oslo"
LANGUAGE_CODE = "en-us"

SITE_ID = 1

USE_I18N = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Static
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# For development only: the repository is public. Production sets its own (MDB_SETTINGS).
SECRET_KEY = "@4ps=ebofcpv8sb#y7gm896=l&l*u0u-pgo7bcdj%+(k+2lqnl"

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    # Serves STATIC_ROOT, so production needs nothing in front but a proxy.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "mdbsite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "rest_framework",
    "rest_framework.authtoken",
    "django_extensions",
    "mdb",
)

EMAIL_SUBJECT_PREFIX = "[MDB] "

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "loggers": {
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

# PXE
MDB_PXE_TFTP_ROOT = "/var/lib/tftpboot/pxelinux/pxelinux.cfg/"
MDB_PXE_KERNEL = "ubuntu/14_04/amd64/alternate/linux"
MDB_PXE_INITRD = "ubuntu/14_04/amd64/alternate/initrd.gz"
MDB_PXE_PRESEED_URL = "http://158.36.190.194/ubuntu/preseed_1404.cfg"

# Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "dev")

ADMIN_SITE_NAME = "MDB"

# Production's settings live outside the code, in the file MDB_SETTINGS names; the mdb role
# in edb-infra writes it. An error in it stops MDB rather than leaving the defaults above.
if os.getenv("MDB_SETTINGS"):
    with open(os.environ["MDB_SETTINGS"]) as f:
        exec(compile(f.read(), os.environ["MDB_SETTINGS"], "exec"))
else:
    # Development. Only a missing local_settings is skipped: a local_settings whose own
    # imports fail must not leave MDB running on the defaults.
    try:
        from .local_settings import *  # noqa: F403
    except ModuleNotFoundError as e:
        if e.name != "mdbsite.local_settings":
            raise
