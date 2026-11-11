import io
import json

import openpyxl
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from estudiantes.models import DocentePerfil
from .base import BaseTestCase, CLAVE_PRUEBA


class MasivoEstudiantesTests(BaseTestCase):
    def setUp(self):
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        self.url = reverse('masivo_estudiantes')

    def test_crea_cuentas_por_lotes_con_clave_igual_al_documento(self):
        ests = [self.crear_estudiante(documento=f'10{i:04d}', apellidos=f'Ape{i}', nombres='Nom', linea='ROB')
                for i in range(45)]
        d = self.client.post(self.url).json()
        self.assertEqual((d['creados'], d['restantes']), (20, 25))
        d = self.client.post(self.url).json()
        self.assertEqual((d['creados'], d['restantes']), (20, 5))
        d = self.client.post(self.url).json()
        self.assertEqual((d['creados'], d['restantes']), (5, 0))
        e = ests[0]; e.refresh_from_db()
        self.assertTrue(e.debe_cambiar_clave)
        self.assertTrue(e.usuario.check_password(e.documento))
        self.assertEqual(e.usuario.username, 'nomape0')
        self.assertEqual(list(e.usuario.groups.values_list('name', flat=True)), ['estudiante'])

    def test_no_toca_a_quien_ya_tiene_cuenta_y_respeta_filtros(self):
        con = self.crear_estudiante_con_acceso(linea='ROB')
        rob = self.crear_estudiante(documento='777', apellidos='R', linea='ROB')
        bio = self.crear_estudiante(documento='888', apellidos='B', linea='BIO')
        antes = con.usuario_id
        self.client.post(self.url, {'linea': 'ROB'})
        rob.refresh_from_db(); bio.refresh_from_db(); con.refresh_from_db()
        self.assertIsNotNone(rob.usuario_id)
        self.assertIsNone(bio.usuario_id)
        self.assertEqual(con.usuario_id, antes)

    def test_nombres_repetidos_reciben_usuario_distinto(self):
        for doc in ('111', '222'):
            self.crear_estudiante(documento=doc, apellidos='Igual', nombres='Mismo')
        self.client.post(self.url)
        self.assertEqual(sorted(User.objects.filter(username__startswith='mismoigual').values_list('username', flat=True)),
                         ['mismoigual', 'mismoigual2'])

    def test_solo_directivo(self):
        self.client.logout()
        self.crear_docente()
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertEqual(self.client.get(reverse('usuarios_masivo')).status_code, 302)


class MasivoDocentesTests(BaseTestCase):
    def setUp(self):
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        self.url = reverse('masivo_docentes')

    def _xlsx(self, filas):
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(['nombres', 'apellidos', 'correo', 'linea', 'jornada'])
        for f in filas:
            ws.append(f)
        b = io.BytesIO(); wb.save(b)
        return SimpleUploadedFile('d.xlsx', b.getvalue())

    def test_crea_docentes_con_linea_y_clave_aleatoria(self):
        r = self.client.post(self.url, {'archivo': self._xlsx([
            ['Ana María', 'Pérez', 'ana@x.co', 'ROB', 'JM'],
            ['Carlos', 'Rojas', '', 'Biotecnología', 'Tarde'],
        ])})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['creados']), 2)
        ana = User.objects.get(username='anamariaperez')
        self.assertEqual((ana.docente_perfil.linea, ana.docente_perfil.jornada), ('ROB', 'JM'))
        self.assertTrue(ana.groups.filter(name='docente').exists())
        clave = r.context['creados'][0]['clave']
        self.assertTrue(ana.check_password(clave))
        carlos = User.objects.get(username='carlosrojas')
        self.assertEqual((carlos.docente_perfil.linea, carlos.docente_perfil.jornada), ('BIO', 'JT'))
        self.client.logout()
        self.assertTrue(self.client.login(username='anamariaperez', password=clave))
        self.assertEqual(self.client.get(reverse('notas')).status_code, 200)

    def test_filas_invalidas_se_reportan_sin_frenar_las_demas(self):
        r = self.client.post(self.url, {'archivo': self._xlsx([
            ['Bien', 'Uno', '', 'ROB', 'JM'],
            ['Mala', 'Linea', '', 'Inexistente', 'JM'],
            ['Mala', 'Jornada', '', 'ROB', 'Noche'],
            ['', '', '', 'ROB', 'JM'],
            ['Mal', 'Correo', 'sin-arroba', 'ROB', 'JM'],
            ['Otro', 'Linea', '', 'OT', 'JM'],
        ])})
        self.assertEqual(len(r.context['creados']), 1)
        self.assertEqual(len(r.context['rechazados']), 4 + 1)

    def test_csv_con_punto_y_coma(self):
        csv_ = 'nombres;apellidos;correo;linea;jornada\nLuis;Mora;;TPS;JT\n'.encode('utf-8')
        r = self.client.post(self.url, {'archivo': SimpleUploadedFile('d.csv', csv_)})
        self.assertEqual(len(r.context['creados']), 1)
        self.assertEqual(DocentePerfil.objects.get(usuario__username='luismora').linea, 'TPS')

    def test_archivo_sin_columnas_o_de_otro_tipo_da_error_claro(self):
        r = self.client.post(self.url, {'archivo': SimpleUploadedFile('d.csv', b'a,b\n1,2\n')})
        self.assertContains(r, 'Faltan columnas')
        r = self.client.post(self.url, {'archivo': SimpleUploadedFile('d.txt', b'x')})
        self.assertContains(r, 'debe ser .xlsx o .csv')

    def test_plantilla_se_descarga(self):
        r = self.client.get(reverse('plantilla_docentes'))
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertEqual([c.value for c in wb['Docentes'][1]], ['nombres', 'apellidos', 'correo', 'linea', 'jornada'])
