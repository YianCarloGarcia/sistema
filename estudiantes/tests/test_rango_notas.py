from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from estudiantes.models import Actividad, CalificacionLinea, NotaActividad
from estudiantes.notas_util import parsear_nota
from .base import CLAVE_PRUEBA, BaseTestCase

INVALIDAS = ['5.01', '6', '7', '10', '50', '-1', '-0.01', 'abc', 'nan', 'inf', '1e3', '4,6,1']
VALIDAS = {'0': '0.00', '5': '5.00', '5.0': '5.00', '4,5': '4.50', '0.0': '0.00', '3.256': '3.26', '2': '2.00'}


class RangoDeNotasTests(BaseTestCase):
    """Una calificación solo puede estar entre 0 y 5: nunca se corrige en silencio ni se guarda fuera de rango."""

    def setUp(self):
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.est = self.crear_estudiante(linea='ROB')
        self.act = Actividad.objects.create(linea='ROB', jornada='JM', nombre='T1', orden=1, creado_por=self.docente)

    # -- parser compartido --
    def test_parser(self):
        for txt in INVALIDAS:
            self.assertIsNone(parsear_nota(txt), txt)
        for txt, esperado in VALIDAS.items():
            self.assertEqual(parsear_nota(txt), Decimal(esperado), txt)

    # -- Notas (por actividad) --
    def _post_notas(self, valor):
        return self.client.post(reverse('notas'), {
            'linea': 'ROB', 'jornada': 'JM', f'nota_{self.est.id}_{self.act.id}': valor}, follow=True)

    def test_notas_rechaza_fuera_de_rango_y_avisa(self):
        for txt in INVALIDAS:
            r = self._post_notas(txt)
            self.assertFalse(NotaActividad.objects.filter(estudiante=self.est).exists(), txt)
            self.assertContains(r, 'NO se guardaron')

    def test_notas_acepta_los_limites(self):
        for txt in ('0', '5', '4,5'):
            NotaActividad.objects.all().delete()
            self._post_notas(txt)
            self.assertEqual(NotaActividad.objects.get(estudiante=self.est).valor, Decimal(VALIDAS[txt]), txt)

    def test_notas_un_valor_malo_no_cambia_la_nota_anterior(self):
        NotaActividad.objects.create(estudiante=self.est, actividad=self.act, valor=Decimal('3.0'))
        self._post_notas('9')
        self.assertEqual(NotaActividad.objects.get(estudiante=self.est).valor, Decimal('3.00'))

    def test_formulario_de_notas_tiene_min_y_max(self):
        r = self.client.get(reverse('notas'))
        self.assertContains(r, 'min="0" max="5"')

    # -- Actividad de línea --
    def test_actividad_linea_rechaza_fuera_de_rango(self):
        for txt in INVALIDAS:
            r = self.client.post(reverse('actividad_linea'), {
                'linea': 'ROB', 'jornada': 'JM', f'nota_{self.est.id}': txt}, follow=True)
            self.assertFalse(CalificacionLinea.objects.filter(estudiante=self.est).exists(), txt)
            self.assertContains(r, 'NO guardado')

    def test_actividad_linea_acepta_limites(self):
        for txt in ('0', '5'):
            CalificacionLinea.objects.all().delete()
            self.client.post(reverse('actividad_linea'), {
                'linea': 'ROB', 'jornada': 'JM', f'nota_{self.est.id}': txt})
            self.assertEqual(CalificacionLinea.objects.get(estudiante=self.est).valor, Decimal(VALIDAS[txt]))

    # -- Base de datos y modelos (admin, scripts, importaciones) --
    def test_base_de_datos_rechaza_notas_fuera_de_rango(self):
        for malo in (Decimal('5.01'), Decimal('-0.5'), Decimal('9.99')):
            with self.assertRaises(IntegrityError), transaction.atomic():
                NotaActividad.objects.create(estudiante=self.est, actividad=self.act, valor=malo)
            with self.assertRaises(IntegrityError), transaction.atomic():
                CalificacionLinea.objects.create(estudiante=self.est, linea='ROB', valor=malo)

    def test_los_modelos_validan_el_rango_para_el_admin(self):
        with self.assertRaises(ValidationError):
            NotaActividad(estudiante=self.est, actividad=self.act, valor=Decimal('5.5')).full_clean()
        with self.assertRaises(ValidationError):
            CalificacionLinea(estudiante=self.est, linea='ROB', valor=Decimal('-1')).full_clean()
        NotaActividad(estudiante=self.est, actividad=self.act, valor=Decimal('5')).full_clean()
