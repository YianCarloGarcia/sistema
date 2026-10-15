"""
Sube al bucket de R2 las fotos de estudiantes que hoy están en el disco local.

Se ejecuta UNA sola vez, desde el computador donde están las fotos (la carpeta
`fotos/`), con las variables R2_* ya definidas:

    python manage.py subir_fotos                # sube todo lo que falte
    python manage.py subir_fotos --dry-run      # solo muestra qué haría
    python manage.py subir_fotos --forzar       # re-sube incluso lo ya existente

No modifica la base de datos: el campo `foto` de cada estudiante ya guarda la
ruta relativa (ej. "fotos/juan.jpg"), y esa misma ruta es la que se usa dentro
del bucket, así que las fotos quedan accesibles sin tocar ningún registro.
"""
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management.base import BaseCommand, CommandError

from estudiantes.models import Estudiante


class Command(BaseCommand):
    help = 'Sube las fotos locales de los estudiantes al almacenamiento de objetos (R2).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Muestra lo que se subiría, sin subir nada.')
        parser.add_argument('--forzar', action='store_true',
                            help='Vuelve a subir las fotos que ya existan en el bucket.')

    def handle(self, *args, **opciones):
        dry_run = opciones['dry_run']
        forzar = opciones['forzar']

        if not getattr(settings, 'USAR_R2', False):
            raise CommandError(
                'Las variables R2_* no están configuradas, así que el destino sería el mismo '
                'disco local. Defina R2_BUCKET, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY y '
                'R2_ENDPOINT_URL antes de ejecutar este comando.'
            )

        # Origen: el disco local, sin importar cuál sea el storage por defecto.
        disco_local = FileSystemStorage(location=settings.MEDIA_ROOT)

        con_foto = Estudiante.objects.exclude(foto='').exclude(foto__isnull=True)
        total = con_foto.count()
        self.stdout.write(f'Estudiantes con foto registrada: {total}')

        subidas = omitidas = faltantes = errores = 0
        nombres_faltantes = []

        for est in con_foto.iterator():
            nombre = est.foto.name  # ej. "fotos/juan_perez.jpg"
            # El campo guarda la ruta con el prefijo "fotos/", pero en disco
            # MEDIA_ROOT ya ES esa carpeta: se quita el prefijo para ubicarlo.
            ruta_relativa = nombre[len('fotos/'):] if nombre.startswith('fotos/') else nombre
            ruta_absoluta = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

            if not os.path.exists(ruta_absoluta):
                faltantes += 1
                nombres_faltantes.append(f'{est.documento} -> {nombre}')
                continue

            if not forzar and default_storage.exists(nombre):
                omitidas += 1
                continue

            if dry_run:
                self.stdout.write(f'  [dry-run] subiría {nombre}')
                subidas += 1
                continue

            try:
                with open(ruta_absoluta, 'rb') as f:
                    if forzar and default_storage.exists(nombre):
                        default_storage.delete(nombre)
                    default_storage.save(nombre, f)
                subidas += 1
                if subidas % 50 == 0:
                    self.stdout.write(f'  ... {subidas} fotos subidas')
            except Exception as exc:
                errores += 1
                self.stderr.write(self.style.ERROR(f'  Error subiendo {nombre}: {exc}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Subidas:  {subidas}'))
        self.stdout.write(f'Omitidas (ya estaban): {omitidas}')
        if faltantes:
            self.stdout.write(self.style.WARNING(
                f'Sin archivo en disco: {faltantes} '
                '(el estudiante tiene foto registrada pero el archivo no existe localmente)'
            ))
            for n in nombres_faltantes[:10]:
                self.stdout.write(f'    {n}')
            if len(nombres_faltantes) > 10:
                self.stdout.write(f'    ... y {len(nombres_faltantes) - 10} más')
        if errores:
            self.stdout.write(self.style.ERROR(f'Errores: {errores}'))
