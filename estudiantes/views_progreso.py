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
    Actividad, ActividadLinea, CalificacionLinea, Estudiante, NIVELES_DESEMPENO, NotaActividad,
    Periodo, RegistroPlanilla, nivel_desempeno,
)
from .periodos import calcular_periodos, puntos_en_periodo
from .models import ConfiguracionPorcentajes
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


# ── Estudiante: proceso del periodo en curso y del año ──────

def _pct(valor):
    """Porcentaje 0–100 para dibujar una nota 0–5 (acotada: una definitiva puede salirse del rango)."""
    if valor is None:
        return 0
    return round(max(0.0, min(5.0, float(valor))) / 5 * 100, 1)


def _num(d):
    return None if d is None else round(float(d), 2)


@login_required
def mi_proceso(request):
    if not _es_estudiante(request.user):
        messages.info(request, "Su cuenta no está asociada a una ficha de estudiante.")
        return redirect('inicio')

    from django.utils import timezone
    hoy = timezone.localdate()
    est = request.user.estudiante_perfil
    actual = Periodo.actual(hoy)
    periodos, datos = calcular_periodos([est.id], actual.anio)
    d = datos[est.id]
    cur = d['periodos'][actual.id]

    # Actividades del periodo en curso con la nota del estudiante.
    notas_obj = {n.actividad_id: n for n in NotaActividad.objects.filter(
        estudiante=est, actividad__periodo=actual)}
    notas = {k: n.valor for k, n in notas_obj.items()}
    actividades = []
    for a in Actividad.objects.filter(linea=est.linea, jornada=est.jornada, periodo=actual):
        valor = notas.get(a.id)
        _k, etiqueta, color = nivel_desempeno(valor) if valor is not None else ('', '', '#94a3b8')
        actividades.append({
            'observacion': notas_obj[a.id].observacion if a.id in notas_obj else '', 'nombre': a.nombre, 'tipo': a.get_tipo_display() if a.tipo != 'GEN' else '', 'valor': _num(valor), 'pct': _pct(valor) if valor is not None else 8,
            'calificada': valor is not None, 'color': color, 'etiqueta': etiqueta,
        })

    # Descuentos / novedades de asistencia dentro del periodo.
    registros = list(RegistroPlanilla.objects.filter(
        estudiante=est, fecha__gte=actual.fecha_inicio, fecha__lte=actual.fecha_fin,
    ).values('estudiante_id', 'fecha', 'bloque', 'estado', 'puntos_aplicados'))
    conteo = {}
    for r in registros:
        c = conteo.setdefault(r['estado'], {'n': 0, 'puntos': Decimal('0')})
        c['n'] += 1
        c['puntos'] += r['puntos_aplicados'] or 0
    maximo = max([c['n'] for c in conteo.values()] or [1])
    novedades = [
        {'estado': cod, 'nombre': nombre, 'n': conteo[cod]['n'], 'puntos': _num(conteo[cod]['puntos']),
         'pct': round(conteo[cod]['n'] / maximo * 100)}
        for cod, nombre in RegistroPlanilla.ESTADOS if cod in conteo and cod != 'A'
    ]

    pesos = ConfiguracionPorcentajes.obtener().por_tipo()
    nombres = {'GEN': 'Actividades generales', 'EVA': 'Evaluación trimestral', 'AUT': 'Autoevaluación'}
    componentes = [
        {'nombre': nombres[t], 'peso': float(pesos[t]), 'valor': _num(cur['componentes'].get(t))}
        for t in ('GEN', 'EVA', 'AUT')
    ]

    total_dias = max((actual.fecha_fin - actual.fecha_inicio).days, 1)
    avance_tiempo = round(max(0, min(total_dias, (hoy - actual.fecha_inicio).days)) / total_dias * 100)

    def nivel(v):
        return nivel_desempeno(max(Decimal('0'), v)) if v is not None else ('', 'Sin nota', '#94a3b8')

    k, etq, col = nivel(cur['definitiva'])
    lista_periodos, anterior = [], None
    for p in periodos:
        x = d['periodos'][p.id]
        estado = 'en curso' if p.id == actual.id else ('cerrado' if p.fecha_fin < hoy else 'próximo')
        delta = None
        if x['definitiva'] is not None and anterior is not None:
            delta = round(float(x['definitiva'] - anterior), 2)
        if x['definitiva'] is not None:
            anterior = x['definitiva']
        lista_periodos.append({
            'id': p.id, 'numero': p.numero, 'estado': estado,
            'inicio': p.fecha_inicio.strftime('%d/%m'), 'fin': p.fecha_fin.strftime('%d/%m'),
            'promedio': _num(x['promedio']), 'puntos': _num(x['puntos']), 'definitiva': _num(x['definitiva']),
            'pct': _pct(x['definitiva']), 'delta': delta, 'n_notas': x['n_notas'],
            'color': nivel(x['definitiva'])[2],
        })
    ka, etqa, cola = nivel(d['anio'])

    datos_js = {
        'periodos': [{'numero': p['numero'], 'definitiva': p['definitiva'], 'estado': p['estado'],
                      'color': p['color']} for p in lista_periodos],
    }
    return render(request, 'estudiantes/mi_proceso.html', {
        'estudiante': est, 'actual': actual, 'anio': actual.anio,
        'cur': {'promedio': _num(cur['promedio']), 'puntos': _num(cur['puntos']),
                'definitiva': _num(cur['definitiva']), 'pct': _pct(cur['definitiva']),
                'nivel': etq, 'color': col},
        'actividades': actividades, 'componentes': componentes, 'novedades': novedades, 'avance_tiempo': avance_tiempo,
        'dias_restantes': max((actual.fecha_fin - hoy).days, 0),
        'periodos': lista_periodos,
        'anual': {'valor': _num(d['anio']), 'pct': _pct(d['anio']), 'nivel': etqa, 'color': cola,
                  'con_nota': sum(1 for p in lista_periodos if p['definitiva'] is not None),
                  'total': len(lista_periodos)},
        'datos_js': datos_js,
    })
