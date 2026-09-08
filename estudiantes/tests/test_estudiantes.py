from django.urls import reverse

from estudiantes.models import Estudiante
from .base import CLAVE_PRUEBA, BaseTestCase


def datos_minimos_estudiante(**overrides):
    datos = {
        'tipo': 'CC',
        'documento': '5550001',
        'jornada': 'JM',
        'apellidos': 'Gómez',
        'nombres': 'Valentina',
        'curso': '1101',
        'linea': 'ROB',
    }
    datos.update(overrides)
    return datos


class CrearEstudianteTests(BaseTestCase):

    def setUp(self):
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)

    def test_crear_estudiante_valido(self):
        respuesta = self.client.post(reverse('crear'), datos_minimos_estudiante(), follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(Estudiante.objects.filter(documento='5550001').exists())

    def test_documento_duplicado_no_crea_un_segundo_registro(self):
        self.client.post(reverse('crear'), datos_minimos_estudiante(documento='5550002'))
        self.assertEqual(Estudiante.objects.filter(documento='5550002').count(), 1)

        respuesta = self.client.post(
            reverse('crear'), datos_minimos_estudiante(documento='5550002', apellidos='Otro Apellido')
        )
        # El formulario rechaza el duplicado (no redirige, vuelve a mostrar el error)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['formulario'].errors.get('documento'))
        self.assertEqual(Estudiante.objects.filter(documento='5550002').count(), 1)


class EditarEstudianteTests(BaseTestCase):

    def setUp(self):
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        self.estudiante = self.crear_estudiante(documento='5550003', apellidos='Original')

    def test_editar_estudiante(self):
        respuesta = self.client.post(
            reverse('editar', args=[self.estudiante.id]),
            datos_minimos_estudiante(documento='5550003', apellidos='Apellido Actualizado'),
            follow=True,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.apellidos, 'Apellido Actualizado')

    def test_editar_no_permite_documento_duplicado_de_otro_estudiante(self):
        otro = self.crear_estudiante(documento='5550004')
        respuesta = self.client.post(
            reverse('editar', args=[self.estudiante.id]),
            datos_minimos_estudiante(documento=otro.documento),
        )
        self.assertEqual(respuesta.status_code, 200)  # se queda en el formulario, no guarda
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.documento, '5550003')


class EliminarEstudianteTests(BaseTestCase):

    def setUp(self):
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        self.estudiante = self.crear_estudiante(documento='5550005')

    def test_eliminar_por_post_funciona(self):
        respuesta = self.client.post(reverse('eliminar', args=[self.estudiante.id]), follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Estudiante.objects.filter(id=self.estudiante.id).exists())

    def test_eliminar_por_get_es_rechazado(self):
        """Una eliminación no debe poder dispararse con un simple enlace/GET."""
        respuesta = self.client.get(reverse('eliminar', args=[self.estudiante.id]))
        self.assertEqual(respuesta.status_code, 405)
        self.assertTrue(Estudiante.objects.filter(id=self.estudiante.id).exists())
