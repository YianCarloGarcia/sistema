"""Reporte de asistencia del estudiante, por semana, a partir de las fechas del periodo.

Se calcula con la planilla del docente (RegistroPlanilla). Cada bloque de clase (fecha + bloque)
se clasifica en uno de estos resultados:
  - EX  excusa justificada (cubre también una falla con excusa en el mismo bloque)
  - F   falla sin excusa
  - E   evasión de clase
  - A   asistió (incluye llegadas tarde o uniforme incompleto: estaba en clase)
La llegada tarde (R) y el uniforme (U) además se cuentan aparte.
Porcentaje de asistencia = asistió / (asistió + fallas + evasiones); las excusas justificadas no
cuentan en contra.
"""
import datetime
from collections import defaultdict

from .models import RegistroPlanilla

RESULTADOS = ('A', 'EX', 'F', 'E')


def clasificar_bloque(estados):
    estados = set(estados)
    if 'EX' in estados:
        return 'EX'
    if 'F' in estados:
        return 'F'
    if 'E' in estados:
        return 'E'
    return 'A'    # A, R, U (solo llegó tarde o sin uniforme): estuvo en clase


def _vacio():
    return {'A': 0, 'EX': 0, 'F': 0, 'E': 0, 'R': 0, 'U': 0}


def _porcentaje(c):
    base = c['A'] + c['F'] + c['E']
    return round(c['A'] / base * 100) if base else None


def reporte_asistencia(estudiante_id, periodos, hoy):
    """Devuelve {periodo.id: {...}} con totales y detalle semanal de cada periodo."""
    periodos = list(periodos)
    if not periodos:
        return {}
    desde = min(p.fecha_inicio for p in periodos)
    hasta = max(p.fecha_fin for p in periodos)
    bloques = defaultdict(list)
    for r in RegistroPlanilla.objects.filter(
            estudiante_id=estudiante_id, fecha__gte=desde, fecha__lte=hasta
    ).values('fecha', 'bloque', 'estado'):
        bloques[(r['fecha'], r['bloque'])].append(r['estado'])

    salida = {}
    for p in periodos:
        total = _vacio()
        semanas = []
        for n in range(1, p.semanas + 1):
            ini = p.fecha_inicio + datetime.timedelta(days=(n - 1) * 7)
            fin = min(ini + datetime.timedelta(days=6), p.fecha_fin)
            semanas.append({'numero': n, 'inicio': ini, 'fin': fin, 'c': _vacio(),
                            'estado': 'futura' if ini > hoy else ('actual' if ini <= hoy <= fin else 'pasada')})
        for (fecha, _b), estados in bloques.items():
            n = p.semana_de(fecha)
            if n is None:
                continue
            res = clasificar_bloque(estados)
            for destino in (total, semanas[n - 1]['c']):
                destino[res] += 1
                if 'R' in estados:
                    destino['R'] += 1
                if 'U' in estados:
                    destino['U'] += 1
        maximo = max([sum(s['c'][k] for k in RESULTADOS) for s in semanas] + [1])
        for s in semanas:
            s['total'] = sum(s['c'][k] for k in RESULTADOS)
            s['alto'] = round(s['total'] / maximo * 100)
        salida[p.id] = {
            'periodo': p,
            'total': total,
            'clases': sum(total[k] for k in RESULTADOS),
            'porcentaje': _porcentaje(total),
            'semanas': semanas,
            'semana_actual': next((s['numero'] for s in semanas if s['estado'] == 'actual'), None),
        }
    return salida
