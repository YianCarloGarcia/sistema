from django.db import migrations


def reclasificar_pp_a_ppt(apps, schema_editor):
    Estudiante = apps.get_model('estudiantes', 'Estudiante')
    Estudiante.objects.filter(tipo='PP').update(tipo='PPT')


def revertir(apps, schema_editor):
    # No se puede distinguir con certeza cuáles PPT eran originalmente PP,
    # así que revertir esta migración no reclasifica nada de vuelta.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('estudiantes', '0029_alter_estudiante_tipo'),
    ]

    operations = [
        migrations.RunPython(reclasificar_pp_a_ppt, revertir),
    ]
