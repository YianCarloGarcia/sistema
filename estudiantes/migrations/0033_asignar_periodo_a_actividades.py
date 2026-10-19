import datetime

from django.db import migrations

FECHAS = {1: ((1, 1), (4, 30)), 2: ((5, 1), (8, 31)), 3: ((9, 1), (12, 31))}


def asignar(apps, schema_editor):
    """Las actividades que ya existían quedan en el periodo que contenía su fecha de creación."""
    Actividad = apps.get_model('estudiantes', 'Actividad')
    Periodo = apps.get_model('estudiantes', 'Periodo')
    for act in Actividad.objects.filter(periodo__isnull=True):
        fecha = act.creado.date() if act.creado else datetime.date.today()
        for numero, ((mi, di), (mf, df)) in FECHAS.items():
            Periodo.objects.get_or_create(anio=fecha.year, numero=numero, defaults={
                'fecha_inicio': datetime.date(fecha.year, mi, di), 'fecha_fin': datetime.date(fecha.year, mf, df),
            })
        act.periodo = (
            Periodo.objects.filter(fecha_inicio__lte=fecha, fecha_fin__gte=fecha).first()
            or Periodo.objects.filter(anio=fecha.year).order_by('numero').first()
        )
        act.save(update_fields=['periodo'])


class Migration(migrations.Migration):
    dependencies = [('estudiantes', '0032_periodos')]
    operations = [migrations.RunPython(asignar, migrations.RunPython.noop)]
