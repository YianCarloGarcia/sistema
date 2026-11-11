from decimal import Decimal

from django.urls import reverse

from estudiantes.models import Actividad, NotaActividad
from .base import CLAVE_PRUEBA, BaseTestCase


class EstudiantesOTTests(BaseTestCase):
    """Los estudiantes con línea OT los ven y evalúan los docentes de todas las líneas."""

    def setUp(self):
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.propio = self.crear_estudiante(apellidos='Propio', linea='ROB')
        self.ot = self.crear_estudiante(apellidos='SinLinea', linea='OT')
        self.ot_tarde = self.crear_estudiante(apellidos='OtroTurno', linea='OT', jornada='JT')
        self.ajeno = self.crear_estudiante(apellidos='Ajeno', linea='BIO')
        self.actividad = Actividad.objects.create(
            linea='ROB', jornada='JM', nombre='Taller 1', orden=1, creado_por=self.docente,
        )

    def test_notas_muestra_ot_y_no_otras_lineas(self):
        r = self.client.get(reverse('notas'))
        ids = {e.id for e in r.context['estudiantes_grupo']}
        self.assertIn(self.propio.id, ids)
        self.assertIn(self.ot.id, ids)
        self.assertNotIn(self.ajeno.id, ids)
        self.assertNotIn(self.ot_tarde.id, ids)

    def test_se_puede_evaluar_a_un_estudiante_ot(self):
        self.client.post(reverse('notas'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': '',
            f'nota_{self.ot.id}_{self.actividad.id}': '4.2',
        })
        nota = NotaActividad.objects.get(estudiante=self.ot, actividad=self.actividad)
        self.assertEqual(nota.valor, Decimal('4.20'))

    def test_al_asignar_linea_deja_de_aparecer_en_otras(self):
        self.ot.linea = 'BIO'
        self.ot.save()
        r = self.client.get(reverse('notas'))
        self.assertNotIn(self.ot.id, {e.id for e in r.context['estudiantes_grupo']})

    def test_planilla_incluye_ot(self):
        r = self.client.get(reverse('planilla'))
        ids = {e.id for e in r.context['estudiantes_grupo']}
        self.assertIn(self.ot.id, ids)
        self.assertNotIn(self.ajeno.id, ids)

    def test_mi_proceso_ot_ve_actividades_de_su_jornada(self):
        est = self.crear_estudiante_con_acceso(linea='OT', jornada='JM')
        self.client.logout()
        self.client.login(username=f'est{est.documento}', password=est.documento)
        r = self.client.get(reverse('mi_proceso'), follow=True)
        self.assertContains(r, 'Taller 1')
