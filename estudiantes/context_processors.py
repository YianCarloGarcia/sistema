"""
Un único punto de verdad para saber el rol del usuario actual dentro de las
plantillas, en vez de que cada plantilla adivine el rol mirando
`request.user.groups.all.0.name` — un patrón frágil que asume que el primer
grupo de la lista es "el" rol, algo que deja de ser cierto en cuanto una
cuenta pertenece a más de un grupo (o simplemente cambia el orden interno
en que Django los devuelve).

Reutiliza exactamente las mismas funciones que ya deciden los permisos reales
en las vistas (`_es_directivo`, `_es_docente`, `_es_estudiante`), así que el
rol que ve la plantilla siempre coincide con el rol que de verdad se aplicó
al permitir o bloquear el acceso — no hay dos fuentes de verdad que puedan
desincronizarse.
"""
from .views import _es_directivo, _es_docente, _es_estudiante


def rol(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'rol_actual': ''}

    if _es_estudiante(user):
        rol_actual = 'estudiante'
    elif _es_directivo(user):
        rol_actual = 'directivo'
    elif _es_docente(user):
        rol_actual = 'docente'
    else:
        rol_actual = ''

    return {
        'rol_actual':       rol_actual,
        'es_directivo_nav':  rol_actual == 'directivo',
        'es_docente_nav':    rol_actual == 'docente',
        'es_estudiante_nav': rol_actual == 'estudiante',
    }
