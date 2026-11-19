import datetime as dt

from django.contrib.admin.sites import site as admin_site
from django.urls import reverse
from django.utils import timezone

from estudiantes.models import Periodo, RegistroPlanilla
from estudiantes.reporte_asistencia import clasificar_bloque, reporte_asistencia
from .base import BaseTestCase


class ReporteAsistenciaTests(BaseTestCase):

    def setUp(self):
        self.inicio = dt.date(2026, 2, 2)    # lunes
        Periodo.objects.all().delete()
        self.p = Periodo.objects.create(anio=2026, numero=1, fecha_inicio=self.inicio,
                                        fecha_fin=Periodo.fin_a_13_semanas(self.inicio))
        self.est = self.crear_estudiante_con_acceso()

    def _reg(self, dias, estado, bloque=1):
        RegistroPlanilla.objects.create(estudiante=self.est, fecha=self.inicio + dt.timedelta(days=dias),
                                        bloque=bloque, estado=estado)

    def test_periodo_de_13_semanas(self):
        self.assertEqual(self.p.semanas, 13)
        self.assertEqual(self.p.fecha_fin, dt.date(2026, 5, 3))   # domingo de la semana 13
        self.assertEqual(self.p.semana_de(self.inicio), 1)
        self.assertEqual(self.p.semana_de(self.inicio + dt.timedelta(days=7)), 2)
        self.assertIsNone(self.p.semana_de(self.p.fecha_fin + dt.timedelta(days=1)))

    def test_clasificacion(self):
        self.assertEqual(clasificar_bloque(['F']), 'F')
        self.assertEqual(clasificar_bloque(['F', 'EX']), 'EX')
        self.assertEqual(clasificar_bloque(['E']), 'E')
        self.assertEqual(clasificar_bloque(['R', 'U']), 'A')
        self.assertEqual(clasificar_bloque(['A']), 'A')

    def test_conteo_por_semana_y_porcentaje(self):
        self._reg(0, 'A'); self._reg(1, 'A'); self._reg(2, 'R')          # semana 1: 3 asistidas (1 tarde)
        self._reg(8, 'F')                                                 # semana 2: falla
        self._reg(9, 'F'); self._reg(9, 'EX')                             # semana 2: excusa
        hoy = self.inicio + dt.timedelta(days=10)
        r = reporte_asistencia(self.est.id, [self.p], hoy)[self.p.id]
        self.assertEqual(r['total']['A'], 3)
        self.assertEqual(r['total']['F'], 1)
        self.assertEqual(r['total']['EX'], 1)
        self.assertEqual(r['total']['R'], 1)
        self.assertEqual(r['porcentaje'], 75)           # 3 / (3 + 1)
        self.assertEqual(len(r['semanas']), 13)
        self.assertEqual(r['semanas'][0]['c']['A'], 3)
        self.assertEqual(r['semanas'][1]['c']['F'], 1)
        self.assertEqual(r['semana_actual'], 2)
        self.assertEqual(r['semanas'][5]['estado'], 'futura')

    def test_ignora_registros_fuera_del_periodo(self):
        self._reg(-5, 'F')
        self._reg(200, 'F')
        r = reporte_asistencia(self.est.id, [self.p], self.inicio)[self.p.id]
        self.assertEqual(r['clases'], 0)
        self.assertIsNone(r['porcentaje'])

    def test_dashboard_muestra_el_reporte(self):
        hoy = timezone.localdate()
        Periodo.objects.all().delete()
        p = Periodo.objects.create(anio=hoy.year, numero=1, fecha_inicio=hoy - dt.timedelta(days=10),
                                   fecha_fin=Periodo.fin_a_13_semanas(hoy - dt.timedelta(days=10)))
        for numero in (2, 3):
            Periodo.objects.create(anio=hoy.year, numero=numero, fecha_inicio=p.fecha_fin + dt.timedelta(days=1) + dt.timedelta(days=(numero - 2) * 91),
                                   fecha_fin=p.fecha_fin + dt.timedelta(days=91) + dt.timedelta(days=(numero - 2) * 91))
        RegistroPlanilla.objects.create(estudiante=self.est, fecha=hoy, bloque=1, estado='F')
        self.client.login(username=self.est.usuario.username, password=self.est.documento)
        r = self.client.get(reverse('mi_proceso'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Mi asistencia en el periodo')
        self.assertEqual(r.context['rep']['total']['F'], 1)
        self.assertEqual(r.context['rep']['periodo'].semanas, 13)

    def test_admin_accion_fija_13_semanas(self):
        self.p.fecha_fin = self.inicio + dt.timedelta(days=30)
        self.p.save()
        self.assertNotEqual(self.p.semanas, 13)
        admin = admin_site._registry[Periodo]
        admin.fijar_fin_a_13_semanas(self._peticion(), Periodo.objects.filter(pk=self.p.pk))
        self.p.refresh_from_db()
        self.assertEqual(self.p.semanas, 13)

    def _peticion(self):
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        req = RequestFactory().post('/')
        req.session = {}
        req._messages = FallbackStorage(req)
        return req

    def test_fecha_fin_debe_ser_posterior(self):
        from django.core.exceptions import ValidationError
        self.p.fecha_fin = self.inicio - dt.timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.p.full_clean()
