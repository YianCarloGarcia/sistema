from django.urls import reverse

from .base import CLAVE_PRUEBA, BaseTestCase


class LoginTests(BaseTestCase):

    def test_login_correcto(self):
        self.crear_directivo(username='directora', password=CLAVE_PRUEBA)
        ok = self.client.login(username='directora', password=CLAVE_PRUEBA)
        self.assertTrue(ok)

        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.status_code, 200)

    def test_login_incorrecto(self):
        self.crear_directivo(username='directora', password=CLAVE_PRUEBA)
        ok = self.client.login(username='directora', password='clave-equivocada')
        self.assertFalse(ok)

        # Sin sesión, una página protegida redirige al login en vez de mostrar contenido
        respuesta = self.client.get(reverse('estudiantes'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/accounts/login/', respuesta.url)

    def test_login_usuario_inexistente(self):
        ok = self.client.login(username='nadie', password='lo-que-sea')
        self.assertFalse(ok)


class CambioClaveObligatorioTests(BaseTestCase):

    def test_cuenta_nueva_es_redirigida_a_cambiar_clave(self):
        estudiante = self.crear_estudiante_con_acceso(debe_cambiar_clave=True)
        self.client.login(username=estudiante.usuario.username, password=estudiante.documento)

        # Cualquier página del sistema debe rebotar a cambiar-clave, no solo el inicio
        for nombre_url in ['inicio', 'mi_historial']:
            respuesta = self.client.get(reverse(nombre_url), follow=False)
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse('cambiar_clave_obligatorio'), respuesta.url)

    def test_cambiar_clave_correctamente_libera_el_acceso(self):
        estudiante = self.crear_estudiante_con_acceso(debe_cambiar_clave=True)
        self.client.login(username=estudiante.usuario.username, password=estudiante.documento)

        respuesta = self.client.post(reverse('cambiar_clave_obligatorio'), {
            'old_password': estudiante.documento,
            'new_password1': 'NuevaClaveSegura2026',
            'new_password2': 'NuevaClaveSegura2026',
        })
        self.assertEqual(respuesta.status_code, 302)

        estudiante.refresh_from_db()
        self.assertFalse(estudiante.debe_cambiar_clave)

        # Ya puede navegar libremente
        respuesta = self.client.get(reverse('mi_historial'))
        self.assertEqual(respuesta.status_code, 200)

        # La contraseña vieja (el documento) ya no debe servir para entrar
        self.client.logout()
        ok_vieja = self.client.login(username=estudiante.usuario.username, password=estudiante.documento)
        ok_nueva = self.client.login(username=estudiante.usuario.username, password='NuevaClaveSegura2026')
        self.assertFalse(ok_vieja)
        self.assertTrue(ok_nueva)

    def test_cuenta_sin_flag_no_es_forzada(self):
        estudiante = self.crear_estudiante_con_acceso(debe_cambiar_clave=False)
        self.client.login(username=estudiante.usuario.username, password=estudiante.documento)

        respuesta = self.client.get(reverse('mi_historial'))
        self.assertEqual(respuesta.status_code, 200)
