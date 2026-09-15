from decimal import Decimal

from django.db import migrations

PUNTOS_POR_DEFECTO = {
    'F':  Decimal('-1'),
    'A':  Decimal('0'),
    'R':  Decimal('-1'),
    'E':  Decimal('-5'),
    'EX': Decimal('0'),
    'U':  Decimal('-1'),
}


def rellenar_puntos_aplicados(apps, schema_editor):
    """
    Rellena 'puntos_aplicados' para los registros que ya existían antes de este
    campo, usando la configuración de puntos VIGENTE HOY (ConfiguracionPuntos, o
    el valor por defecto si no hay fila configurada para ese estado).

    Esto es una aproximación, no un dato histórico real: si la configuración de
    puntos cambió en algún momento del pasado, no hay forma de reconstruir con
    certeza qué valor estaba vigente el día exacto en que se creó cada registro
    antiguo. De aquí en adelante, cada registro nuevo (o cada vez que se ajuste
    el estado de uno existente) sí queda con el valor exacto que tenía la
    configuración en ese momento, y esos valores ya no se mueven aunque la
    configuración cambie después.
    """
    ConfiguracionPuntos = apps.get_model('estudiantes', 'ConfiguracionPuntos')
    RegistroPlanilla = apps.get_model('estudiantes', 'RegistroPlanilla')

    puntos_config = dict(PUNTOS_POR_DEFECTO)
    puntos_config.update(dict(ConfiguracionPuntos.objects.values_list('estado', 'puntos')))

    for estado, puntos in puntos_config.items():
        RegistroPlanilla.objects.filter(estado=estado).update(puntos_aplicados=puntos)


def revertir(apps, schema_editor):
    RegistroPlanilla = apps.get_model('estudiantes', 'RegistroPlanilla')
    RegistroPlanilla.objects.update(puntos_aplicados=0)


class Migration(migrations.Migration):

    dependencies = [
        ('estudiantes', '0026_registroplanilla_puntos_aplicados'),
    ]

    operations = [
        migrations.RunPython(rellenar_puntos_aplicados, revertir),
    ]
