from decimal import Decimal

from django.urls import reverse

from estudiantes.models import Actividad, NotaActividad
from .base import CLAVE_PRUEBA, BaseTestCase


class EstudiantesOTTests(BaseTestCase):
    """OT = estudiantes sin línea. Es una opción de la lista «Línea y jornada» (clasificada por
    jornada y curso) y cada docente califica a los OT con SUS actividades de línea."""

    def setUp(self):
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.propio = self.crear_estudiante(apellidos='Propio', linea='ROB', curso='1001', grado='10')
        self.ot_a = self.crear_estudiante(apellidos='OtA', linea='OT', curso='1001', grado='10')
        self.ot_b = self.crear_estudiante(apellidos='OtB', linea='OT', curso='1102', grado='11')
        self.ot_tarde = self.crear_estudiante(apellidos='OtroTurno', linea='OT', jornada='JT', curso='1001')
        self.ajeno = self.crear_estudiante(apellidos='Ajeno', linea='BIO')
        self.actividad = Actividad.objects.create(
            linea='ROB', jornada='JM', nombre='Taller 1', orden=1, creado_por=self.docente)

    def _ids(self, nombre_url, **params):
        r = self.client.get(reverse(nombre_url), params)
        self.assertEqual(r.status_code, 200)
        ctx = r.context
        ids = {e.id for e in ctx['estudiantes_grupo']} if 'estudiantes_grupo' in ctx else \
            {f['estudiante'].id for f in ctx['filas']}
        return r, ids

    def test_vista_normal_solo_estudiantes_de_la_linea(self):
        for url in ('notas', 'planilla', 'actividad_linea'):
            _, ids = self._ids(url)
            self.assertEqual(ids, {self.propio.id}, url)

    def test_la_lista_del_docente_ofrece_ot(self):
        for url in ('notas', 'planilla', 'actividad_linea'):
            r, _ = self._ids(url)
            self.assertEqual([g[:3] for g in r.context['grupos_disponibles']],
                             [('ROB', 'JM', ''), ('OT', 'JM', 'OT')], url)
            self.assertContains(r, 'OT Mañana')
            self.assertNotContains(r, 'OT Tarde')   # solo la jornada del docente

    def test_ot_por_jornada_con_la_linea_del_docente(self):
        for url in ('notas', 'planilla', 'actividad_linea'):
            r, ids = self._ids(url, grado='OT')
            self.assertEqual(ids, {self.ot_a.id, self.ot_b.id}, url)      # ni el de la tarde ni de otras líneas
            self.assertEqual(r.context['linea'], 'ROB', url)               # se califica en SU línea
            self.assertTrue([g for g in r.context['grupos_disponibles'] if g[2] == 'OT' and g[3]], url)

    def test_ot_por_curso(self):
        r, ids = self._ids('notas', grado='OT-1102')
        self.assertEqual(ids, {self.ot_b.id})
        self.assertEqual(r.context['grados_disponibles'],
                         [('OT', 'Todos los cursos'), ('OT-1001', '1001'), ('OT-1102', '1102')])
        self.assertContains(r, '>Curso</label>')

    def test_se_califica_con_las_actividades_de_la_propia_linea(self):
        self.client.post(reverse('notas'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': 'OT',
            f'nota_{self.ot_a.id}_{self.actividad.id}': '4.2'})
        self.assertEqual(NotaActividad.objects.get(estudiante=self.ot_a, actividad=self.actividad).valor,
                         Decimal('4.20'))

    def test_dos_docentes_califican_al_mismo_ot_con_sus_lineas(self):
        otro = self.crear_docente(username='docente2', linea='BIO', jornada='JM')
        act_bio = Actividad.objects.create(linea='BIO', jornada='JM', nombre='Lab', orden=1, creado_por=otro)
        self.client.post(reverse('notas'), {'grado': 'OT', f'nota_{self.ot_a.id}_{self.actividad.id}': '3.0'})
        self.client.logout()
        self.client.login(username='docente2', password=CLAVE_PRUEBA)
        self.client.post(reverse('notas'), {'grado': 'OT', f'nota_{self.ot_a.id}_{act_bio.id}': '5.0'})
        self.assertEqual(NotaActividad.objects.filter(estudiante=self.ot_a).count(), 2)

    def test_al_asignar_linea_deja_de_ser_ot(self):
        self.ot_a.linea = 'BIO'
        self.ot_a.save()
        _, ids = self._ids('notas', grado='OT')
        self.assertNotIn(self.ot_a.id, ids)

    def test_actividad_de_linea_califica_en_la_linea_del_docente(self):
        from estudiantes.models import CalificacionLinea
        self.client.post(reverse('actividad_linea'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': 'OT', f'nota_{self.ot_a.id}': '4.5'})
        self.assertEqual(CalificacionLinea.objects.get(estudiante=self.ot_a, linea='ROB').valor, Decimal('4.50'))

    def test_exportar_ot(self):
        r = self.client.get(reverse('exportar_planilla'), {'grado': 'OT-1001'})
        self.assertEqual(r.status_code, 200)

    def test_directivo_elige_linea_y_ot(self):
        self.client.logout()
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        for url in ('notas', 'planilla', 'actividad_linea'):
            r, ids = self._ids(url, linea='BIO', jornada='JM', grado='OT')
            claves = [g[:3] for g in r.context['grupos_disponibles']]
            self.assertIn(('BIO', 'JM', ''), claves, url)
            self.assertIn(('OT', 'JM', 'OT'), claves, url)
            self.assertIn(('OT', 'JT', 'OT'), claves, url)                          # directivo ve ambas jornadas
            self.assertEqual(ids, {self.ot_a.id, self.ot_b.id}, url)
            self.assertContains(r, 'OT Mañana'); self.assertContains(r, 'OT Tarde')
            if url != 'planilla':
                self.assertContains(r, 'Calificar en la línea')

    def test_directivo_ot_sin_linea_usa_una_por_defecto(self):
        self.client.logout()
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        r, ids = self._ids('notas', linea='', jornada='JM', grado='OT')
        self.assertEqual(r.context['linea'], 'AA')
        self.assertEqual(ids, {self.ot_a.id, self.ot_b.id})
        r, ids = self._ids('notas', linea='OT', jornada='JM')      # enlace antiguo
        self.assertEqual(ids, {self.ot_a.id, self.ot_b.id})

    def test_estudiante_ot_ve_la_nota_de_cada_linea(self):
        from estudiantes.models import CalificacionLinea
        est = self.crear_estudiante_con_acceso(linea='OT', jornada='JM')
        CalificacionLinea.objects.create(estudiante=est, linea='ROB', valor=Decimal('4.0'))
        CalificacionLinea.objects.create(estudiante=est, linea='BIO', valor=Decimal('3.5'))
        NotaActividad.objects.create(estudiante=est, actividad=self.actividad, valor=Decimal('4.4'))
        self.client.logout()
        self.client.login(username=est.usuario.username, password=est.documento)
        r = self.client.get(reverse('mi_progreso'))
        calificadas = {l['codigo'] for l in r.context['lineas'] if l['calificada']}
        self.assertEqual(calificadas, {'ROB', 'BIO'})
        r = self.client.get(reverse('mi_proceso'))
        self.assertContains(r, 'ROB · Taller 1')

    def test_historial_tambien_ofrece_ot(self):
        r = self.client.get(reverse('historial_planilla'), {'grado': 'OT'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'OT Mañana')
        self.assertContains(r, '>Curso</label>')
