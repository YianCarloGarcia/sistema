from django.db import migrations

GRADOS_CONOCIDOS = {'10', '11'}


def rellenar_grado(apps, schema_editor):
    Estudiante = apps.get_model('estudiantes', 'Estudiante')
    for est in Estudiante.objects.filter(grado='').exclude(curso=''):
        prefijo = (est.curso or '').strip()[:2]
        if prefijo in GRADOS_CONOCIDOS:
            est.grado = prefijo
            est.save(update_fields=['grado'])


def revertir(apps, schema_editor):
    Estudiante = apps.get_model('estudiantes', 'Estudiante')
    Estudiante.objects.update(grado='')


class Migration(migrations.Migration):

    dependencies = [
        ('estudiantes', '0024_estudiante_grado'),
    ]

    operations = [
        migrations.RunPython(rellenar_grado, revertir),
    ]
