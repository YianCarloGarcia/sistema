import time

from django.urls import reverse

from estudiantes.models import Asistencia
from .base import CLAVE_PRUEBA, BaseTestCase


class EscanerTests(BaseTestCase):

    def setUp(self):
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        self.estudiante = self.crear_estudiante(documento='6660001')

    def _escanear(self, documento, tipo='ALM'):
        return self.client.post(reverse('escaner_registrar'), {'documento': documento, 'tipo': tipo})

    def test_documento_existente_registra_correctamente(self):
        respuesta = self._escanear(self.estudiante.documento)
        data = respuesta.json()
        self.assertTrue(data['ok'])
        self.assertIn(self.estudiante.nombres, data['nombre'])
        self.assertEqual(data['contador'], 1)
        self.assertEqual(Asistencia.objects.filter(estudiante=self.estudiante, tipo='ALM').count(), 1)

    def test_documento_inexistente_no_registra_nada(self):
        respuesta = self._escanear('99999999999')
        data = respuesta.json()
        self.assertFalse(data['ok'])
        self.assertEqual(Asistencia.objects.count(), 0)

    def test_documento_vacio_es_rechazado(self):
        respuesta = self._escanear('')
        data = respuesta.json()
        self.assertFalse(data['ok'])

    def test_segundo_escaneo_inmediato_queda_bloqueado(self):
        primero = self._escanear(self.estudiante.documento)
        self.assertTrue(primero.json()['ok'])

        segundo = self._escanear(self.estudiante.documento)
        data = segundo.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data.get('tipo'), 'espera')
        # No debe haber creado un segundo registro
        self.assertEqual(Asistencia.objects.filter(estudiante=self.estudiante, tipo='ALM').count(), 1)

    def test_tipos_distintos_no_se_bloquean_entre_si(self):
        """Escanear para ALM no debe bloquear un escaneo de TAR del mismo estudiante."""
        self._escanear(self.estudiante.documento, tipo='ALM')
        respuesta = self._escanear(self.estudiante.documento, tipo='TAR')
        self.assertTrue(respuesta.json()['ok'])

    def test_contador_incrementa_solo_despues_de_pasar_el_bloqueo(self):
        self._escanear(self.estudiante.documento)
        # Forzamos el registro anterior a "hace rato" para simular que ya pasó el bloqueo
        registro = Asistencia.objects.get(estudiante=self.estudiante, tipo='ALM')
        registro.hora = (
            __import__('datetime').datetime.combine(registro.fecha, registro.hora)
            - __import__('datetime').timedelta(seconds=10)
        ).time()
        registro.save()

        respuesta = self._escanear(self.estudiante.documento)
        data = respuesta.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['contador'], 2)

    def test_escaner_requiere_autenticacion(self):
        self.client.logout()
        respuesta = self._escanear(self.estudiante.documento)
        self.assertEqual(respuesta.status_code, 302)

    def test_escaner_requiere_metodo_post(self):
        respuesta = self.client.get(reverse('escaner_registrar'))
        self.assertEqual(respuesta.status_code, 405)
