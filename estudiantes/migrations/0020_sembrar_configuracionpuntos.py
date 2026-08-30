from django.db import migrations

VALORES_INICIALES = {
    'F':  -1,
    'A':   0,
    'R':  -1,
    'E':  -5,
    'EX':  0,
    'U':  -1,
}


def sembrar_puntos(apps, schema_editor):
    ConfiguracionPuntos = apps.get_model('estudiantes', 'ConfiguracionPuntos')
    for estado, puntos in VALORES_INICIALES.items():
        ConfiguracionPuntos.objects.get_or_create(estado=estado, defaults={'puntos': puntos})


def revertir(apps, schema_editor):
    ConfiguracionPuntos = apps.get_model('estudiantes', 'ConfiguracionPuntos')
    ConfiguracionPuntos.objects.filter(estado__in=VALORES_INICIALES.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('estudiantes', '0019_configuracionpuntos'),
    ]

    operations = [
        migrations.RunPython(sembrar_puntos, revertir),
    ]
