import io
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .base import CLAVE_PRUEBA, BaseTestCase

MEDIA = tempfile.mkdtemp(prefix='fotos_test_carnet_')


def _jpg():
    buf = io.BytesIO()
    Image.new('RGB', (60, 80), 'blue').save(buf, 'JPEG')
    return buf.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class CarnetEstudianteTests(BaseTestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def _entrar(self, nombre_foto=None, **kw):
        est = self.crear_estudiante_con_acceso(linea='ROB', jornada='JM', curso='1001', **kw)
        if nombre_foto:
            est.foto.save(nombre_foto, ContentFile(_jpg()), save=True)
        self.client.login(username=est.usuario.username, password=est.documento)
        return est

    def test_sin_foto_no_habilita_la_descarga(self):
        self._entrar()
        r = self.client.get(reverse('mi_carnet'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context['habilitado'])
        self.assertContains(r, 'disabled')
        self.assertNotContains(r, reverse('mi_carnet_png') + '?descargar=1')

    def test_foto_default_en_cualquiera_de_sus_formas_no_cuenta(self):
        for nombre in ('foto_default.jpg', 'foto_default_Ab12Cd.jpg', 'Foto_Default 2025.jpg',
                       'foto_default-colegio.jpg'):
            self.client.logout()
            est = self._entrar(nombre)
            self.assertFalse(est.tiene_foto_real, nombre)
            r = self.client.get(reverse('mi_carnet'))
            self.assertFalse(r.context['habilitado'], nombre)
            # el acceso directo a la imagen tampoco funciona
            r = self.client.get(reverse('mi_carnet_png'), {'descargar': 1})
            self.assertEqual(r.status_code, 302, nombre)
            est.usuario.delete()
            est.delete()

    def test_con_foto_propia_se_habilita_y_descarga_png(self):
        est = self._entrar('1234567890.jpg')
        self.assertTrue(est.tiene_foto_real)
        r = self.client.get(reverse('mi_carnet'))
        self.assertTrue(r.context['habilitado'])
        self.assertContains(r, 'Descargar mi carnet')
        self.assertContains(r, reverse('mi_carnet_png') + '?descargar=1')
        r = self.client.get(reverse('mi_carnet_png'), {'descargar': 1})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'image/png')
        self.assertIn(f'carnet_{est.documento}.png', r['Content-Disposition'])
        self.assertIn('no-store', r['Cache-Control'])
        img = Image.open(io.BytesIO(r.content))
        self.assertEqual(img.size, (540, 860))

    def test_vista_previa_no_fuerza_descarga(self):
        self._entrar('mia.jpg')
        r = self.client.get(reverse('mi_carnet_png'))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('Content-Disposition', r)

    def test_la_foto_aparece_en_el_carnet(self):
        """La foto se lee con el almacenamiento (válido también para R2), no con una ruta de disco."""
        self._entrar('mia.jpg')
        r = self.client.get(reverse('mi_carnet_png'))
        img = Image.open(io.BytesIO(r.content)).convert('RGB')
        azules = sum(1 for p in img.getdata() if p[2] > 200 and p[0] < 60 and p[1] < 60)
        self.assertGreater(azules, 5000)     # el recuadro azul de la foto de prueba (240×290 px)

    def test_el_estudiante_solo_ve_su_carnet(self):
        otro = self.crear_estudiante(documento='999', apellidos='Otro')
        otro.foto.save('otro.jpg', ContentFile(_jpg()), save=True)
        self._entrar('mia.jpg')
        r = self.client.get(reverse('mi_carnet_png') + '?id=' + str(otro.id) + '&documento=999')
        self.assertIn(b'PNG', r.content[:8])
        self.assertNotIn('999', r.get('Content-Disposition', ''))

    def test_docente_y_anonimo_no_acceden(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('mi_carnet')).status_code, 302)
        self.assertEqual(self.client.get(reverse('mi_carnet_png')).status_code, 302)
        self.crear_docente()
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.assertEqual(self.client.get(reverse('mi_carnet')).status_code, 302)
        self.assertEqual(self.client.get(reverse('mi_carnet_png')).status_code, 302)

    def test_aparece_en_el_menu_del_estudiante(self):
        self._entrar('mia.jpg')
        self.assertContains(self.client.get(reverse('inicio')), reverse('mi_carnet'))
