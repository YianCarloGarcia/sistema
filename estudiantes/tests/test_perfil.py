import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .base import CLAVE_PRUEBA, BaseTestCase


def _png(nombre='f.png'):
    buf = io.BytesIO()
    Image.new('RGB', (20, 20), 'red').save(buf, 'PNG')
    return SimpleUploadedFile(nombre, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT='/tmp/fotos_test_perfil')
class PerfilDocenteTests(BaseTestCase):

    def setUp(self):
        self.docente = self.crear_docente()
        self.client.login(username='docente1', password=CLAVE_PRUEBA)

    def test_editar_datos(self):
        self.client.post(reverse('mi_perfil'), {
            'accion': 'datos', 'first_name': 'Ana', 'last_name': 'Gómez', 'email': 'ana@x.co'})
        u = User.objects.get(pk=self.docente.pk)
        self.assertEqual((u.first_name, u.last_name, u.email), ('Ana', 'Gómez', 'ana@x.co'))

    def test_correo_invalido(self):
        self.client.post(reverse('mi_perfil'), {
            'accion': 'datos', 'first_name': 'Ana', 'last_name': 'G', 'email': 'malo'})
        self.assertEqual(User.objects.get(pk=self.docente.pk).email, '')

    def test_subir_y_quitar_foto(self):
        self.client.post(reverse('mi_perfil'), {'accion': 'foto', 'foto': _png()})
        self.docente.docente_perfil.refresh_from_db()
        self.assertTrue(self.docente.docente_perfil.foto)
        self.client.post(reverse('mi_perfil'), {'accion': 'foto', 'quitar': 'on'})
        self.docente.docente_perfil.refresh_from_db()
        self.assertFalse(self.docente.docente_perfil.foto)

    def test_archivo_que_no_es_imagen(self):
        malo = SimpleUploadedFile('a.png', b'no es imagen', content_type='image/png')
        self.client.post(reverse('mi_perfil'), {'accion': 'foto', 'foto': malo})
        self.docente.docente_perfil.refresh_from_db()
        self.assertFalse(self.docente.docente_perfil.foto)

    def test_cambiar_clave_mantiene_sesion(self):
        r = self.client.post(reverse('mi_perfil'), {
            'accion': 'clave', 'old_password': CLAVE_PRUEBA,
            'new_password1': 'NuevaClave#2026x', 'new_password2': 'NuevaClave#2026x'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.get(pk=self.docente.pk).check_password('NuevaClave#2026x'))
        self.assertEqual(self.client.get(reverse('mi_perfil')).status_code, 200)

    def test_clave_actual_incorrecta(self):
        self.client.post(reverse('mi_perfil'), {
            'accion': 'clave', 'old_password': 'mala',
            'new_password1': 'NuevaClave#2026x', 'new_password2': 'NuevaClave#2026x'})
        self.assertTrue(User.objects.get(pk=self.docente.pk).check_password(CLAVE_PRUEBA))

    def test_estudiante_no_accede(self):
        self.client.logout()
        est = self.crear_estudiante_con_acceso()
        self.client.login(username=f'est{est.documento}', password=est.documento)
        self.assertEqual(self.client.get(reverse('mi_perfil')).status_code, 302)
