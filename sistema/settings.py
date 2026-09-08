from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# En producción, defina la variable de entorno DJANGO_SECRET_KEY con una clave
# nueva y secreta (nunca la que trae este archivo). Ejemplo para generarla:
#   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# El valor de respaldo de abajo solo se usa si la variable no está definida
# (por ejemplo, en desarrollo local) y está marcado como inseguro a propósito.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-(d-$cb%v22^)f=lqp+)ec+!0e+(sxbq3xw(7kl!$w=ya)kds00',
)

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'estudiantes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'estudiantes.middleware.ForzarCambioClaveMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sistema.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'estudiantes.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
# Destino de `python manage.py collectstatic` para cuando se sirva con DEBUG=False
# (necesario sobre todo para que el admin de Django cargue su propio CSS/JS).
# No tiene ningún efecto mientras DEBUG siga en True, así que es seguro definirlo ya.
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = os.path.join(BASE_DIR, 'fotos')
MEDIA_URL = '/fotos/'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── Email via Outlook / Hotmail ──────────────────────────────
# Las credenciales NUNCA deben quedar escritas en este archivo (que suele terminar
# en el control de versiones). Se toman de variables de entorno del servidor:
#   export EMAIL_USER='su_correo@outlook.com'
#   export EMAIL_PASSWORD='contraseña de aplicación'
# En desarrollo local, si no se definen, se usa un backend de consola que solo
# imprime el correo en la terminal (no intenta conectarse a ningún servidor real).
EMAIL_HOST_USER     = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST    = 'smtp-mail.outlook.com'
    EMAIL_PORT    = 587
    EMAIL_USE_TLS = True
else:
    # Sin credenciales configuradas: no se rompe el arranque, solo se imprime
    # el correo en consola. Revise las variables de entorno antes de producción.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'no-reply@localhost'

# ── Cabeceras de seguridad (no dependen de HTTPS ni de ALLOWED_HOSTS) ────────
# Deliberadamente NO se incluyen aquí SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE,
# CSRF_COOKIE_SECURE ni SECURE_HSTS_SECONDS: esas requieren que el sitio ya esté
# sirviendo por HTTPS con un dominio real, y se configurarán en el paso en que se
# ajuste ALLOWED_HOSTS/el dominio de producción.
SECURE_CONTENT_TYPE_NOSNIFF = True   # evita que el navegador "adivine" tipos de archivo
SECURE_REFERRER_POLICY = 'same-origin'  # no filtra la URL completa a sitios externos
X_FRAME_OPTIONS = 'DENY'             # el sitio no puede incrustarse en un <iframe> ajeno
