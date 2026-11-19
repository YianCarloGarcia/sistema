from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ForzarCambioClaveMiddleware:
    """
    Ya no obliga a cambiar la contraseña al iniciar sesión por primera vez: el cambio es
    opcional y el estudiante lo hace cuando quiera desde «Contraseña» (url `cambiar_clave_obligatorio`,
    nombre conservado por compatibilidad). El middleware se mantiene como paso transparente
    para no tocar la configuración. `debe_cambiar_clave` solo sirve para mostrar un aviso.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
