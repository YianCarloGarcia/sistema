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

# DEBUG se apaga automáticamente en producción definiendo DJANGO_DEBUG=0.
# Si la variable no existe (desarrollo local en Windows), sigue en True como antes.
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

# Dominios desde los que se puede servir la app, separados por coma.
# Ej: DJANGO_ALLOWED_HOSTS='sistema.up.railway.app,colegio.edu.co'
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()
]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Railway expone el dominio asignado en esta variable; se agrega solo.
_railway_host = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '').strip()
if _railway_host and _railway_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_host)

# Django 4+ exige declarar el origen completo (con https://) para validar CSRF.
CSRF_TRUSTED_ORIGINS = [
    f'https://{h}' for h in ALLOWED_HOSTS if h not in ('localhost', '127.0.0.1', 'testserver')
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'estudiantes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise sirve los archivos estáticos (CSS, JS, iconos) sin necesidad de
    # Nginx. Debe ir inmediatamente después de SecurityMiddleware.
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
                'estudiantes.context_processors.rol',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema.wsgi.application'

# ── Base de datos ─────────────────────────────────────────────
# Si se definen las variables de entorno de PostgreSQL (DB_NAME y DB_USER),
# se usa PostgreSQL — la opción recomendada para producción. Si no están
# definidas, se sigue usando SQLite automáticamente (útil para desarrollo
# local sin tener que instalar Postgres). No hace falta tocar este archivo
# para alternar entre los dos: basta con definir o quitar las variables.
DB_NAME     = os.environ.get('DB_NAME', '')
DB_USER     = os.environ.get('DB_USER', '')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_HOST     = os.environ.get('DB_HOST', 'localhost')
DB_PORT     = os.environ.get('DB_PORT', '5432')

if DB_NAME and DB_USER:
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     DB_NAME,
            'USER':     DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST':     DB_HOST,
            'PORT':     DB_PORT,
            # Reutiliza conexiones hasta 60s en vez de abrir/cerrar una por
            # cada request — reduce bastante la latencia bajo carga real.
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'estudiantes.sqlite3',
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
# Destino de `python manage.py collectstatic`. WhiteNoise sirve desde aquí en producción.
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = os.path.join(BASE_DIR, 'fotos')
MEDIA_URL = '/fotos/'

# ── Almacenamiento de las fotos de estudiantes ───────────────
# En Railway (y en cualquier plataforma de contenedores) el disco es EFÍMERO: todo
# lo que se guarde en el disco del servidor se BORRA en cada despliegue o reinicio.
# Por eso las fotos NO pueden vivir en MEDIA_ROOT en producción; van a un bucket
# de almacenamiento de objetos (Cloudflare R2, compatible con S3).
#
# Si se definen las variables R2_*, las fotos se guardan y se leen del bucket.
# Si no, se sigue usando el disco local exactamente como hasta ahora (desarrollo).
R2_BUCKET             = os.environ.get('R2_BUCKET', '')
R2_ACCESS_KEY_ID      = os.environ.get('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY  = os.environ.get('R2_SECRET_ACCESS_KEY', '')
R2_ENDPOINT_URL       = os.environ.get('R2_ENDPOINT_URL', '')   # https://<account_id>.r2.cloudflarestorage.com
R2_PUBLIC_URL         = os.environ.get('R2_PUBLIC_URL', '')     # dominio público del bucket

USAR_R2 = all([R2_BUCKET, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL])

if USAR_R2:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                'bucket_name':           R2_BUCKET,
                'access_key':            R2_ACCESS_KEY_ID,
                'secret_key':            R2_SECRET_ACCESS_KEY,
                'endpoint_url':          R2_ENDPOINT_URL,
                'region_name':           'auto',
                'signature_version':     's3v4',
                'default_acl':           None,   # R2 no usa ACLs al estilo S3
                'querystring_auth':      False,  # URLs limpias, sin firma temporal
                'file_overwrite':        False,  # no pisar una foto con otra del mismo nombre
                'custom_domain':         R2_PUBLIC_URL.replace('https://', '').replace('http://', '') or None,
            },
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': (
                'whitenoise.storage.CompressedManifestStaticFilesStorage'
                if not DEBUG
                else 'django.contrib.staticfiles.storage.StaticFilesStorage'
            ),
        },
    }

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

# ── Cabeceras de seguridad ───────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True   # evita que el navegador "adivine" tipos de archivo
SECURE_REFERRER_POLICY = 'same-origin'  # no filtra la URL completa a sitios externos
X_FRAME_OPTIONS = 'DENY'             # el sitio no puede incrustarse en un <iframe> ajeno

if not DEBUG:
    # Estas solo tienen sentido con HTTPS ya funcionando. Railway (como casi todas
    # las plataformas) termina el TLS en su proxy y reenvía la petición por HTTP
    # interno: esta cabecera es la que le dice a Django que el usuario SÍ venía
    # por HTTPS. Sin ella, SECURE_SSL_REDIRECT entraría en un bucle de redirección.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True   # la cookie de sesión no viaja por HTTP plano
    CSRF_COOKIE_SECURE = True
    # HSTS: empezar con 1 hora para probar. Subir a 31536000 (1 año) solo cuando
    # esté seguro de que el dominio siempre servirá por HTTPS — es difícil de revertir.
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
