"""
Carga (o quita) calificaciones de ejemplo en el módulo «Actividad de línea» para poder
ver las gráficas del estudiante sin esperar a que los docentes califiquen.

    python manage.py demo_progreso            # califica con notas de ejemplo
    python manage.py demo_progreso --borrar   # elimina SOLO las notas de ejemplo

Las notas de ejemplo llevan la observación «[demo]», así que nunca se confunden con
las reales y --borrar jamás toca una nota registrada por un docente.
"""
import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from estudiantes.models import CalificacionLinea, Estudiante

MARCA = '[demo]'


class Command(BaseCommand):
    help = "Carga o elimina calificaciones de ejemplo del módulo de actividad por línea."

    def add_arguments(self, parser):
        parser.add_argument('--borrar', action='store_true', help='Elimina las notas de ejemplo.')
        parser.add_argument('--todas-las-lineas', action='store_true',
                            help='Califica a cada estudiante en las 7 líneas (por defecto solo en la suya).')

    def handle(self, *args, **opts):
        if opts['borrar']:
            n, _ = CalificacionLinea.objects.filter(observacion=MARCA).delete()
            self.stdout.write(self.style.SUCCESS(f"{n} nota(s) de ejemplo eliminada(s)."))
            return

        rng = random.Random(2026)
        lineas = [c for c, _ in Estudiante.LINEA_MEDIA if c != 'OT']
        creadas = 0
        for est in Estudiante.objects.exclude(linea='OT'):
            destino = lineas if opts['todas_las_lineas'] else [est.linea]
            for linea in destino:
                if CalificacionLinea.objects.filter(estudiante=est, linea=linea).exists():
                    continue   # nunca pisa una nota existente
                valor = Decimal(str(round(min(5, max(1.5, rng.gauss(3.8, 0.8))), 1)))
                CalificacionLinea.objects.create(estudiante=est, linea=linea, valor=valor, observacion=MARCA)
                creadas += 1
        self.stdout.write(self.style.SUCCESS(f"{creadas} nota(s) de ejemplo creada(s)."))
