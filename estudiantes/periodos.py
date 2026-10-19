"""
Cálculo de notas por periodo académico y del año completo.

Definitiva de un periodo = promedio de las notas de las actividades de ese periodo
+ puntos de asistencia (descuentos) de las fechas de ese periodo — la misma fórmula
que ya usa la pantalla de Notas. Sin notas en el periodo, la definitiva queda vacía (None).
Definitiva del año = promedio de las definitivas de los periodos que ya la tienen.
"""
from decimal import Decimal

from .models import NotaActividad, Periodo, RegistroPlanilla

DOS = Decimal('0.01')


def puntos_en_periodo(registros, periodo):
    """{estudiante_id: puntos} solo con los registros cuya fecha cae dentro del periodo."""
    dentro = [r for r in registros if periodo.fecha_inicio <= r['fecha'] <= periodo.fecha_fin]
    return RegistroPlanilla.calcular_puntos_por_estudiante(dentro)


def calcular_periodos(estudiante_ids, anio, periodos=None):
    """Devuelve (periodos, datos) con datos = {est_id: {'periodos': {periodo_id: {...}}, 'anio': Decimal|None}}.
    Usa tres consultas para todo el grupo, sin importar cuántos estudiantes sean."""
    if periodos is None:
        Periodo.asegurar_anio(anio)
        periodos = list(Periodo.objects.filter(anio=anio).order_by('numero'))
    ids = list(estudiante_ids)
    notas = {}
    for est_id, per_id, valor in NotaActividad.objects.filter(
        estudiante_id__in=ids, actividad__periodo__in=periodos,
    ).values_list('estudiante_id', 'actividad__periodo_id', 'valor'):
        notas.setdefault((est_id, per_id), []).append(valor)

    registros = list(RegistroPlanilla.objects.filter(
        estudiante_id__in=ids, fecha__gte=periodos[0].fecha_inicio, fecha__lte=periodos[-1].fecha_fin,
    ).values('estudiante_id', 'fecha', 'bloque', 'estado', 'puntos_aplicados'))
    puntos = {p.id: puntos_en_periodo(registros, p) for p in periodos}

    datos = {}
    for est_id in ids:
        por_periodo, definitivas = {}, []
        for p in periodos:
            valores = notas.get((est_id, p.id), [])
            promedio = (sum(valores) / len(valores)).quantize(DOS) if valores else None
            pts = Decimal(puntos[p.id].get(est_id, 0))
            definitiva = (promedio + pts).quantize(DOS) if promedio is not None else None
            por_periodo[p.id] = {'promedio': promedio, 'puntos': pts, 'definitiva': definitiva, 'n_notas': len(valores)}
            if definitiva is not None:
                definitivas.append(definitiva)
        datos[est_id] = {
            'periodos': por_periodo,
            'anio': (sum(definitivas) / len(definitivas)).quantize(DOS) if definitivas else None,
        }
    return periodos, datos
