"""
Módulo «Actividad por línea»: cada una de las siete líneas de media tiene una actividad
(con el nombre de la línea) que su docente califica de 0.0 a 5.0, y el estudiante ve su
resultado de forma gráfica y animada en /mi-progreso/.

Vive en su propio archivo para no tocar el resto de las vistas.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import redirect, render

from .models import (
    ActividadLinea, CalificacionLinea, Estudiante, NIVELES_DESEMPENO, nivel_desempeno,
)
from .views import (
    _es_estudiante, _puede_usar_planilla, _resolver_grupo, bloquear_estudiantes,
)

LINEAS_MEDIA = [c for c in Estudiante.LINEA_MEDIA if c[0] != 'OT']
CODIGOS_LINEAS = [c[0] for c in LINEAS_MEDIA]


def _parsear_nota(texto):
    """Convierte '4,5' / '4.5' en Decimal acotado a 0–5 con dos decimales; None si es inválido."""
    try:
        valor = Decimal(str(texto).strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None
    if not valor.is_finite():
        return None
    return max(Decimal('0'), min(Decimal('5'), valor)).quantize(Decimal('0.01'))


# ── Docente / directivo ─────────────────────────────────────

@login_required
@bloquear_estudiantes
def actividad_linea(request):
    if not _puede_usar_planilla(request.user):
        messages.error(request, "Su cuenta no tiene una línea asignada. Pida a un directivo que se la asigne.")
        return redirect('inicio')

    (es_directivo, linea, jornada, grado_filtro, grupos_disponibles,
     grados_disponibles, estudiantes_grupo) = _resolver_grupo(request)

    if linea not in CODIGOS_LINEAS:
        # «Otro» (OT) o vacío no tiene actividad: el directivo elige una línea válida.
        linea = ''
        estudiantes_grupo = Estudiante.objects.none()

    actividad = ActividadLinea.objects.filter(linea=linea).first() if linea else None
    estudiantes = list(estudiantes_grupo)

    if request.method == 'POST' and linea and jornada:
        ids_validos = {e.id for e in estudiantes}
        existentes = {c.estudiante_id: c for c in CalificacionLinea.objects.filter(linea=linea, estudiante_id__in=ids_validos)}
        guardadas = borradas = invalidas = 0

        with transaction.atomic():
            descripcion = request.POST.get('descripcion', '').strip()[:2000]
            ActividadLinea.objects.update_or_create(linea=linea, defaults={'descripcion': descripcion})

            for est in estudiantes:
                actual = existentes.get(est.id)
                if request.POST.get(f'borrar_{est.id}') == '1':
                    if actual:
                        actual.delete()
                        borradas += 1
                    continue
                texto = request.POST.get(f'nota_{est.id}', '').strip()
                obs = request.POST.get(f'obs_{est.id}', '').strip()[:200]
                if texto == '':
                    # Casilla vacía = no tocar (el borrado es explícito, como en Notas).
                    if actual and actual.observacion != obs:
                        actual.observacion = obs
                        actual.save(update_fields=['observacion', 'actualizado'])
                    continue
                valor = _parsear_nota(texto)
                if valor is None:
                    invalidas += 1
                    continue
                if actual:
                    if actual.valor != valor or actual.observacion != obs:
                        actual.valor, actual.observacion, actual.registrado_por = valor, obs, request.user
                        actual.save()
                        guardadas += 1
                else:
                    CalificacionLinea.objects.create(
                        estudiante=est, linea=linea, valor=valor, observacion=obs, registrado_por=request.user,
                    )
                    guardadas += 1

        partes = [f"{guardadas} nota(s) guardada(s)"]
        if borradas:
            partes.append(f"{borradas} borrada(s)")
        if invalidas:
            partes.append(f"{invalidas} valor(es) no válido(s) ignorado(s)")
        messages.success(request, "Actividad guardada: " + ", ".join(partes) + ".")
        query = f"?linea={linea}&jornada={jornada}" + (f"&grado={grado_filtro}" if grado_filtro else "")
        return redirect(f"{request.path}{query}")

    notas = {c.estudiante_id: c for c in CalificacionLinea.objects.filter(
        linea=linea, estudiante_id__in=[e.id for e in estudiantes])} if linea else {}
    filas = [{'estudiante': e, 'calificacion': notas.get(e.id)} for e in estudiantes]
    valores = [c.valor for c in notas.values()]
    resumen = {
        'total': len(estudiantes),
        'calificados': len(valores),
        'promedio': (sum(valores) / len(valores)).quantize(Decimal('0.01')) if valores else None,
        'aprobados': sum(1 for v in valores if v >= Decimal('3.0')),
    }

    return render(request, 'estudiantes/actividad_linea.html', {
        'es_directivo': es_directivo,
        'linea': linea,
        'linea_nombre': dict(LINEAS_MEDIA).get(linea, ''),
        'jornada': jornada,
        'grado_filtro': grado_filtro,
        'grupos_disponibles': [g for g in grupos_disponibles if g[0] in CODIGOS_LINEAS],
        'grados_disponibles': grados_disponibles,
        'actividad': actividad,
        'filas': filas,
        'resumen': resumen,
    })


# ── Estudiante ──────────────────────────────────────────────

@login_required
def mi_progreso(request):
    if not _es_estudiante(request.user):
        messages.info(request, "Su cuenta no está asociada a una ficha de estudiante.")
        return redirect('inicio')

    estudiante = request.user.estudiante_perfil
    propias = {c.linea: c for c in CalificacionLinea.objects.filter(estudiante=estudiante)}
    descripciones = dict(ActividadLinea.objects.values_list('linea', 'descripcion'))

    # Promedio por línea (mismo grado si se conoce); solo se muestra con 3+ notas.
    promedios = {}
    base = CalificacionLinea.objects.all()
    if estudiante.grado:
        base = base.filter(estudiante__grado=estudiante.grado)
    for fila in base.values('linea').annotate(prom=Avg('valor'), n=Count('id')):
        promedios[fila['linea']] = fila

    lineas = []
    for codigo, nombre in LINEAS_MEDIA:
        cal = propias.get(codigo)
        prom = promedios.get(codigo)
        item = {
            'codigo': codigo, 'nombre': nombre, 'es_mia': codigo == estudiante.linea,
            'descripcion': descripciones.get(codigo, ''),
            'calificada': cal is not None,
            'valor': None, 'porcentaje': 0, 'nivel': None, 'etiqueta': '', 'color': '#94a3b8',
            'observacion': '', 'promedio_grupo': None, 'porcentaje_grupo': 0,
        }
        if cal is not None:
            clave, etiqueta, color = nivel_desempeno(cal.valor)
            item.update(
                valor=float(cal.valor), porcentaje=round(float(cal.valor) / 5 * 100, 1),
                nivel=clave, etiqueta=etiqueta, color=color, observacion=cal.observacion,
            )
        if prom and prom['n'] >= 3:   # solo se muestra con 3+ notas, para no identificar a nadie
            item['promedio_grupo'] = round(float(prom['prom']), 2)
            item['porcentaje_grupo'] = round(float(prom['prom']) / 5 * 100, 1)
        lineas.append(item)

    calificadas = [l for l in lineas if l['calificada']]
    principal = next((l for l in lineas if l['es_mia']), None)
    if principal is None or not principal['calificada']:
        principal = calificadas[0] if calificadas else None

    # Siguiente nivel a alcanzar para la actividad principal.
    siguiente = None
    if principal:
        for minimo, clave, etiqueta, _color in sorted(NIVELES_DESEMPENO, key=lambda n: n[0]):
            if Decimal(str(principal['valor'])) < minimo:
                siguiente = {'etiqueta': etiqueta, 'minimo': float(minimo),
                             'faltan': round(float(minimo) - principal['valor'], 2)}
                break

    promedio_general = round(sum(l['valor'] for l in calificadas) / len(calificadas), 2) if calificadas else None
    return render(request, 'estudiantes/mi_progreso.html', {
        'estudiante': estudiante,
        'lineas': lineas,
        'principal': principal,
        'siguiente': siguiente,
        'calificadas': len(calificadas),
        'total_lineas': len(lineas),
        'promedio_general': promedio_general,
        'niveles': [
            {'etiqueta': e, 'minimo': float(m), 'color': c}
            for m, _k, e, c in sorted(NIVELES_DESEMPENO, key=lambda n: n[0])
        ],
    })
