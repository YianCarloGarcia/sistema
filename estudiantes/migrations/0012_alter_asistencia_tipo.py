from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estudiantes', '0011_alter_asistencia_fecha'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asistencia',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('ALM', 'Almuerzo'),
                    ('TAR', 'Llegada tarde'),
                    ('UNI', 'Porte de uniforme'),
                    ('ASI', 'Asistencia a clase'),
                ],
                default='ALM',
                max_length=20,
            ),
        ),
    ]
