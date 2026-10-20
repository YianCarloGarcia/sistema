"""
Cálculo de notas por periodo académico y del año completo.

Definitiva de un periodo = promedio de las notas de las actividades de ese periodo
+ puntos de asistencia (descuentos) de las fechas de ese periodo — la misma fórmula
que ya usa la pantalla de Notas. Sin notas en el periodo, la definitiva queda vacía (None).
Definitiva del año = promedio de las definitivas de los periodos que ya la tienen.
"""
from decimal import Decimal

from .models import ConfiguracionPorcentajes, NotaActividad, Periodo, RegistroPlanilla

DOS = Decimal('0.01')


def promedio_ponderado(valores_por_tipo, pesos):
    """Promedio ponderado de la nota del periodo.

    `valores_por_tipo`: {'GEN': [notas], 'EVA': [notas], 'AUT': [notas]}; cada tipo se promedia
    por separado y luego se pondera con `pesos` (porcentajes). Si todavía falta algún tipo
    (por ejemplo la evaluación aún no se aplica), el cálculo se reparte entre los tipos que sí
    tienen nota, de modo que el avance parcial es justo y, con solo actividades generales,
    equivale al promedio simple de siempre. Devuelve (promedio | None, {tipo: promedio_tipo})."""
    componentes = {t: sum(Decimal(str(x)) for x in v) / len(v) for t, v in valores_por_tipo.items() if v}
    if not componentes:
        return None, {}
    total = sum(Decimal(pesos[t]) for t in componentes)
    if total <= 0:
        return (sum(componentes.values()) / len(componentes)).quantize(DOS), componentes
    prom = sum(Decimal(pesos[t]) * c for t, c in componentes.items()) / total
    return prom.quantize(DOS), componentes


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
    pesos = ConfiguracionPorcentajes.obtener().por_tipo()
    notas = {}
    for est_id, per_id, tipo, valor in NotaActividad.objects.filter(
        estudiante_id__in=ids, actividad__periodo__in=periodos,
    ).values_list('estudiante_id', 'actividad__periodo_id', 'actividad__tipo', 'valor'):
        notas.setdefault((est_id, per_id), {}).setdefault(tipo, []).append(valor)

    registros = list(RegistroPlanilla.objects.filter(
        estudiante_id__in=ids, fecha__gte=periodos[0].fecha_inicio, fecha__lte=periodos[-1].fecha_fin,
    ).values('estudiante_id', 'fecha', 'bloque', 'estado', 'puntos_aplicados'))
    puntos = {p.id: puntos_en_periodo(registros, p) for p in periodos}

    datos = {}
    for est_id in ids:
        por_periodo, definitivas = {}, []
        for p in periodos:
            por_tipo = notas.get((est_id, p.id), {})
            promedio, componentes = promedio_ponderado(por_tipo, pesos)
            pts = Decimal(puntos[p.id].get(est_id, 0))
            definitiva = (promedio + pts).quantize(DOS) if promedio is not None else None
            por_periodo[p.id] = {'promedio': promedio, 'puntos': pts, 'definitiva': definitiva, 'n_notas': sum(len(v) for v in por_tipo.values()),
                                      'componentes': componentes}
            if definitiva is not None:
                definitivas.append(definitiva)
        datos[est_id] = {
            'periodos': por_periodo,
            'anio': (sum(definitivas) / len(definitivas)).quantize(DOS) if definitivas else None,
        }
    return periodos, datos


def promedio_de_estudiante(notas_por_actividad, tipo_por_actividad, pesos):
    """Atajo para las pantallas de Notas y el exporte: {actividad_id: nota} -> promedio ponderado."""
    por_tipo = {}
    for actividad_id, valor in notas_por_actividad.items():
        por_tipo.setdefault(tipo_por_actividad.get(actividad_id, 'GEN'), []).append(valor)
    return promedio_ponderado(por_tipo, pesos)[0]
