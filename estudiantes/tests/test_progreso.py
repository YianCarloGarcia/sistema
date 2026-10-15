from decimal import Decimal

from django.test import override_settings
from django.urls import reverse

from estudiantes.models import ActividadLinea, CalificacionLinea, nivel_desempeno
from .base import BaseTestCase, CLAVE_PRUEBA


class NivelesTests(BaseTestCase):
    def test_limites_de_nivel(self):
        self.assertEqual(nivel_desempeno('2.99')[0], 'bajo')
        self.assertEqual(nivel_desempeno('3.0')[0], 'basico')
        self.assertEqual(nivel_desempeno('4.0')[0], 'alto')
        self.assertEqual(nivel_desempeno('4.6')[0], 'superior')
        self.assertEqual(nivel_desempeno('5')[0], 'superior')


class ActividadLineaDocenteTests(BaseTestCase):
    def setUp(self):
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.e1 = self.crear_estudiante(linea='ROB', jornada='JM', apellidos='A')
        self.e2 = self.crear_estudiante(linea='ROB', jornada='JM', apellidos='B')
        self.otra = self.crear_estudiante(linea='BIO', jornada='JM', apellidos='C')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.url = reverse('actividad_linea')

    def test_docente_califica_con_coma_decimal(self):
        r = self.client.post(self.url, {'descripcion': 'Proyecto', f'nota_{self.e1.id}': '4,5', f'nota_{self.e2.id}': ''})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(CalificacionLinea.objects.get(estudiante=self.e1).valor, Decimal('4.50'))
        self.assertFalse(CalificacionLinea.objects.filter(estudiante=self.e2).exists())
        self.assertEqual(ActividadLinea.objects.get(linea='ROB').descripcion, 'Proyecto')

    def test_nota_se_acota_y_texto_invalido_se_ignora(self):
        self.client.post(self.url, {f'nota_{self.e1.id}': '9', f'nota_{self.e2.id}': 'abc'})
        self.assertEqual(CalificacionLinea.objects.get(estudiante=self.e1).valor, Decimal('5.00'))
        self.assertFalse(CalificacionLinea.objects.filter(estudiante=self.e2).exists())

    def test_casilla_vacia_no_borra_pero_borrar_explicito_si(self):
        CalificacionLinea.objects.create(estudiante=self.e1, linea='ROB', valor=Decimal('3.5'))
        self.client.post(self.url, {f'nota_{self.e1.id}': ''})
        self.assertTrue(CalificacionLinea.objects.filter(estudiante=self.e1).exists())
        self.client.post(self.url, {f'borrar_{self.e1.id}': '1'})
        self.assertFalse(CalificacionLinea.objects.filter(estudiante=self.e1).exists())

    def test_docente_no_califica_estudiantes_de_otra_linea(self):
        self.client.post(self.url, {f'nota_{self.otra.id}': '5'})
        self.assertFalse(CalificacionLinea.objects.filter(estudiante=self.otra).exists())

    def test_docente_no_puede_cambiar_de_linea_por_parametros(self):
        self.client.post(self.url, {'linea': 'BIO', 'jornada': 'JM', f'nota_{self.otra.id}': '5'})
        self.assertFalse(CalificacionLinea.objects.filter(estudiante=self.otra).exists())

    def test_pantalla_muestra_nota_guardada(self):
        CalificacionLinea.objects.create(estudiante=self.e1, linea='ROB', valor=Decimal('4.2'))
        r = self.client.get(self.url)
        self.assertContains(r, 'value="4.20"')

    def test_directivo_elige_linea(self):
        self.client.logout()
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        self.client.post(self.url, {'linea': 'BIO', 'jornada': 'JM', f'nota_{self.otra.id}': '4'})
        self.assertEqual(CalificacionLinea.objects.get(estudiante=self.otra).valor, Decimal('4.00'))

    def test_estudiante_no_entra_a_la_pantalla_del_docente(self):
        self.client.logout()
        est = self.crear_estudiante_con_acceso(linea='ROB')
        self.client.login(username=est.usuario.username, password=est.documento)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse('mi_historial'), fetch_redirect_response=False)

    def test_anonimo_es_redirigido(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


class MiProgresoTests(BaseTestCase):
    def test_sin_notas_muestra_mensaje(self):
        est = self.crear_estudiante_con_acceso(linea='ROB')
        self.client.login(username=est.usuario.username, password=est.documento)
        r = self.client.get(reverse('mi_progreso'))
        self.assertContains(r, 'Aún no tienes calificaciones')

    def test_estudiante_ve_su_nota_y_nivel(self):
        est = self.crear_estudiante_con_acceso(linea='ROB')
        CalificacionLinea.objects.create(estudiante=est, linea='ROB', valor=Decimal('4.3'))
        self.client.login(username=est.usuario.username, password=est.documento)
        r = self.client.get(reverse('mi_progreso'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Alto')
        self.assertContains(r, 'data-valor="4.30"')
        self.assertEqual(r.context['principal']['codigo'], 'ROB')
        self.assertEqual(r.context['siguiente']['etiqueta'], 'Superior')

    def test_no_ve_notas_de_otros_estudiantes(self):
        est = self.crear_estudiante_con_acceso(linea='ROB')
        otro = self.crear_estudiante(linea='ROB', apellidos='Otro', nombres='Ajeno')
        CalificacionLinea.objects.create(estudiante=otro, linea='ROB', valor=Decimal('1.1'), observacion='privado')
        self.client.login(username=est.usuario.username, password=est.documento)
        r = self.client.get(reverse('mi_progreso'))
        self.assertNotContains(r, 'privado')
        self.assertIsNone(r.context['principal'])

    def test_promedio_del_grupo_solo_con_tres_o_mas_notas(self):
        est = self.crear_estudiante_con_acceso(linea='ROB', curso='1101')
        CalificacionLinea.objects.create(estudiante=est, linea='ROB', valor=Decimal('4'))
        for i in range(2):
            o = self.crear_estudiante(linea='ROB', curso='1101', apellidos=f'X{i}')
            CalificacionLinea.objects.create(estudiante=o, linea='ROB', valor=Decimal('2'))
        self.client.login(username=est.usuario.username, password=est.documento)
        rob = next(l for l in self.client.get(reverse('mi_progreso')).context['lineas'] if l['codigo'] == 'ROB')
        self.assertEqual(rob['promedio_grupo'], 2.67)

    def test_docente_no_entra_a_mi_progreso(self):
        self.crear_docente()
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        r = self.client.get(reverse('mi_progreso'))
        self.assertRedirects(r, reverse('inicio'), fetch_redirect_response=False)

    def test_siete_lineas_sin_otro(self):
        est = self.crear_estudiante_con_acceso(linea='ROB')
        self.client.login(username=est.usuario.username, password=est.documento)
        r = self.client.get(reverse('mi_progreso'))
        self.assertEqual(len(r.context['lineas']), 7)
