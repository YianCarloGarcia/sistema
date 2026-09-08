from decimal import Decimal

from django.urls import reverse

from estudiantes.models import Actividad, NotaActividad
from .base import CLAVE_PRUEBA, BaseTestCase


class NotasTests(BaseTestCase):

    def setUp(self):
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.estudiante = self.crear_estudiante(curso='1101', jornada='JM', linea='ROB')
        self.actividad = Actividad.objects.create(
            linea='ROB', jornada='JM', nombre='Taller 1', orden=1, creado_por=self.docente,
        )

    def _guardar_nota(self, valor, estudiante=None, actividad=None):
        estudiante = estudiante or self.estudiante
        actividad = actividad or self.actividad
        return self.client.post(reverse('notas'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': '',
            f'nota_{estudiante.id}_{actividad.id}': valor,
        })

    def test_crear_nota(self):
        self._guardar_nota('4.5')
        nota = NotaActividad.objects.get(estudiante=self.estudiante, actividad=self.actividad)
        self.assertEqual(nota.valor, Decimal('4.50'))

    def test_modificar_nota_existente(self):
        self._guardar_nota('3.0')
        self._guardar_nota('4.8')
        nota = NotaActividad.objects.get(estudiante=self.estudiante, actividad=self.actividad)
        self.assertEqual(nota.valor, Decimal('4.80'))
        self.assertEqual(NotaActividad.objects.filter(estudiante=self.estudiante, actividad=self.actividad).count(), 1)

    def test_dejar_la_casilla_en_blanco_no_borra_la_nota(self):
        """Regresión: guardar el formulario con la casilla vacía (sin tocar el botón de
        borrar) debe conservar la nota que ya existía."""
        self._guardar_nota('4.0')
        self._guardar_nota('')
        nota = NotaActividad.objects.get(estudiante=self.estudiante, actividad=self.actividad)
        self.assertEqual(nota.valor, Decimal('4.00'))

    def test_eliminar_nota_explicitamente(self):
        self._guardar_nota('4.0')
        self.assertTrue(NotaActividad.objects.filter(estudiante=self.estudiante, actividad=self.actividad).exists())

        self.client.post(reverse('notas'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': '',
            f'nota_{self.estudiante.id}_{self.actividad.id}': '',
            f'borrar_{self.estudiante.id}_{self.actividad.id}': 'on',
        })
        self.assertFalse(NotaActividad.objects.filter(estudiante=self.estudiante, actividad=self.actividad).exists())

    def test_nota_por_encima_de_5_se_recorta_a_5(self):
        self._guardar_nota('9.7')
        nota = NotaActividad.objects.get(estudiante=self.estudiante, actividad=self.actividad)
        self.assertEqual(nota.valor, Decimal('5.00'))

    def test_nota_negativa_se_recorta_a_0(self):
        self._guardar_nota('-3')
        nota = NotaActividad.objects.get(estudiante=self.estudiante, actividad=self.actividad)
        self.assertEqual(nota.valor, Decimal('0.00'))

    def test_valor_no_numerico_se_ignora_sin_error(self):
        respuesta = self._guardar_nota('abc')
        self.assertEqual(respuesta.status_code, 302)  # no debe romperse
        self.assertFalse(NotaActividad.objects.filter(estudiante=self.estudiante, actividad=self.actividad).exists())

    def test_docente_de_otra_linea_no_ve_la_actividad(self):
        self.crear_docente(username='docente2', linea='TPS', jornada='JM')
        self.client.logout()
        self.client.login(username='docente2', password=CLAVE_PRUEBA)

        respuesta = self.client.get(reverse('notas'))
        self.assertNotIn(self.actividad, list(respuesta.context['actividades']))
