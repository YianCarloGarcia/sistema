from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estudiantes', '0012_alter_asistencia_tipo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estudiante',
            name='foto',
            field=models.ImageField(blank=True, null=True, upload_to='fotos/'),
        ),
    ]
