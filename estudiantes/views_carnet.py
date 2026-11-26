"""Carnet del estudiante: vista previa y descarga desde su propia cuenta."""
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .utils.carnet_png import generar_carnet_png
from .views import _es_estudiante


def _estudiante_o_none(request):
    if not _es_estudiante(request.user):
        return None
    return request.user.estudiante_perfil


@login_required
def mi_carnet(request):
    estudiante = _estudiante_o_none(request)
    if estudiante is None:
        messages.info(request, "Su cuenta no está asociada a una ficha de estudiante.")
        return redirect('inicio')
    return render(request, 'estudiantes/mi_carnet.html', {
        'estudiante': estudiante,
        'habilitado': estudiante.tiene_foto_real,
    })


@login_required
def mi_carnet_png(request):
    """Imagen del carnet del propio estudiante (sin parámetros de identidad: nadie ve el de otro).
    Con ?descargar=1 se entrega como archivo. Solo si el estudiante tiene fotografía propia."""
    estudiante = _estudiante_o_none(request)
    if estudiante is None:
        return redirect('inicio')
    if not estudiante.tiene_foto_real:
        messages.warning(request, "Su carnet estará disponible cuando su fotografía esté registrada en el sistema.")
        return redirect('mi_carnet')
    try:
        imagen = generar_carnet_png(estudiante)
    except ValueError:
        messages.error(request, "No se pudo generar su carnet en este momento. Avise a coordinación.")
        return redirect('mi_carnet')

    buffer = io.BytesIO()
    imagen.save(buffer, format='PNG')
    respuesta = HttpResponse(buffer.getvalue(), content_type='image/png')
    respuesta['Cache-Control'] = 'private, no-store'          # contiene datos personales
    if request.GET.get('descargar'):
        respuesta['Content-Disposition'] = f'attachment; filename="carnet_{estudiante.documento}.png"'
    return respuesta
