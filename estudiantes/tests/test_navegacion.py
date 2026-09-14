from django.urls import reverse

from .base import CLAVE_PRUEBA, BaseTestCase


class RolEnPlantillasTests(BaseTestCase):
    """Verifica que el context processor 'rol' (que reemplazó a
    request.user.groups.all.0.name) muestre la insignia y el menú correctos
    para cada tipo de cuenta."""

    def test_insignia_directivo(self):
        self.crear_directivo(username='directora')
        self.client.login(username='directora', password=CLAVE_PRUEBA)
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'Directivo')
        self.assertContains(respuesta, reverse('lista_usuarios'))  # ve el menú de usuarios

    def test_insignia_superusuario_muestra_admin(self):
        self.crear_directivo(username='root', superuser=True)
        self.client.login(username='root', password=CLAVE_PRUEBA)
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'Admin')

    def test_insignia_docente(self):
        self.crear_docente(username='profe1', linea='ROB', jornada='JM')
        self.client.login(username='profe1', password=CLAVE_PRUEBA)
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'Docente')
        self.assertContains(respuesta, reverse('planilla'))     # sí ve planilla/notas
        self.assertNotContains(respuesta, reverse('lista_usuarios'))  # no ve usuarios

    def test_insignia_estudiante_y_menu_reducido(self):
        estudiante = self.crear_estudiante_con_acceso()
        self.client.login(username=estudiante.usuario.username, password=estudiante.documento)
        respuesta = self.client.get(reverse('mi_historial'))
        self.assertContains(respuesta, 'Estudiante')
        self.assertContains(respuesta, reverse('mi_historial'))
        self.assertNotContains(respuesta, reverse('estudiantes'))
        self.assertNotContains(respuesta, reverse('lista_usuarios'))

    def test_lista_usuarios_marca_directivos_correctamente(self):
        self.crear_directivo(username='directora2')
        self.crear_docente(username='profe2', linea='ROB', jornada='JM')
        self.client.login(username='directora2', password=CLAVE_PRUEBA)

        respuesta = self.client.get(reverse('lista_usuarios'))
        self.assertContains(respuesta, 'Directivo')
        self.assertContains(respuesta, 'Docente')
