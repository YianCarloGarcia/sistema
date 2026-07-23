from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ForzarCambioClaveMiddleware:
    """
    Si una cuenta de estudiante tiene `debe_cambiar_clave = True` (recién creada
    o restablecida por un directivo), se le obliga a cambiar la contraseña antes
    de poder ver cualquier otra página del sistema.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated and hasattr(user, 'estudiante_perfil'):
            estudiante = user.estudiante_perfil
            if estudiante.debe_cambiar_clave:
                rutas_permitidas = {
                    reverse('cambiar_clave_obligatorio'),
                    reverse('exit'),
                }
                permitido = (
                    request.path in rutas_permitidas
                    or request.path.startswith(settings.STATIC_URL)
                    or request.path.startswith(settings.MEDIA_URL)
                )
                if not permitido:
                    return redirect('cambiar_clave_obligatorio')

        return self.get_response(request)
