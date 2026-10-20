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


class UsuarioEstudianteDesdePanelTests(BaseTestCase):
    def setUp(self):
        self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)
        self.ficha = self.crear_estudiante(documento='1234567890', linea='ROB')

    def _datos(self, **extra):
        d = {'username': 'ana.perez', 'first_name': 'Ana', 'last_name': 'Pérez', 'email': '',
             'password1': 'Clave-Segura-9876', 'password2': 'Clave-Segura-9876',
             'rol': 'estudiante', 'estudiante_documento': '1234567890'}
        d.update(extra)
        return d

    def test_crear_estudiante_lo_vincula_y_exige_cambio_de_clave(self):
        r = self.client.post(reverse('crear_usuario'), self._datos())
        self.assertRedirects(r, reverse('lista_usuarios'), fetch_redirect_response=False)
        self.ficha.refresh_from_db()
        u = self.ficha.usuario
        self.assertEqual(u.username, 'ana.perez')
        self.assertTrue(self.ficha.debe_cambiar_clave)
        self.assertEqual(list(u.groups.values_list('name', flat=True)), ['estudiante'])
        self.assertFalse(u.is_staff)

    def test_documento_inexistente_o_ya_con_cuenta_se_rechaza(self):
        r = self.client.post(reverse('crear_usuario'), self._datos(estudiante_documento='000'))
        self.assertEqual(r.status_code, 200)
        self.client.post(reverse('crear_usuario'), self._datos())
        r = self.client.post(reverse('crear_usuario'), self._datos(username='otro'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'ya tiene una cuenta')

    def test_correo_sigue_siendo_obligatorio_para_docente(self):
        r = self.client.post(reverse('crear_usuario'), self._datos(rol='directivo'))
        self.assertEqual(r.status_code, 200)

    def test_cuenta_de_estudiante_no_se_puede_convertir_en_docente(self):
        est = self.crear_estudiante_con_acceso(linea='ROB')
        r = self.client.post(reverse('editar_usuario', args=[est.usuario.id]), {
            'username': est.usuario.username, 'first_name': 'x', 'last_name': 'y', 'email': '',
            'is_active': 'on', 'rol': 'docente', 'grupo_linea': 'ROB', 'grupo_jornada': 'JM'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(est.usuario.groups.values_list('name', flat=True)), ['estudiante'])

    def test_editar_estudiante_conserva_rol(self):
        est = self.crear_estudiante_con_acceso(linea='ROB')
        r = self.client.post(reverse('editar_usuario', args=[est.usuario.id]), {
            'username': est.usuario.username, 'first_name': 'Nuevo', 'last_name': 'Nombre', 'email': '',
            'is_active': 'on', 'rol': 'estudiante'})
        self.assertRedirects(r, reverse('lista_usuarios'), fetch_redirect_response=False)
        est.usuario.refresh_from_db()
        self.assertEqual(est.usuario.first_name, 'Nuevo')
        self.assertTrue(hasattr(est.usuario, 'estudiante_perfil'))


class PeriodosTests(BaseTestCase):
    def setUp(self):
        from datetime import date
        from estudiantes.models import Periodo
        for n, (a, b) in {1: ((1, 1), (4, 30)), 2: ((5, 1), (8, 31)), 3: ((9, 1), (12, 31))}.items():
            Periodo.objects.get_or_create(anio=2026, numero=n, defaults={
                'fecha_inicio': date(2026, *a), 'fecha_fin': date(2026, *b)})
        self.p1, self.p2, self.p3 = (Periodo.objects.get(anio=2026, numero=n) for n in (1, 2, 3))
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.est = self.crear_estudiante_con_acceso(linea='ROB', jornada='JM')

    def _act(self, periodo, nombre='Taller'):
        from estudiantes.models import Actividad
        return Actividad.objects.create(linea='ROB', jornada='JM', nombre=nombre, periodo=periodo)

    def test_periodo_actual_por_fecha(self):
        from datetime import date
        from estudiantes.models import Periodo
        self.assertEqual(Periodo.actual(date(2026, 6, 10)).numero, 2)
        self.assertEqual(Periodo.actual(date(2026, 10, 15)).numero, 3)

    def test_actividad_sin_periodo_usa_el_actual(self):
        from estudiantes.models import Actividad, Periodo
        a = Actividad.objects.create(linea='ROB', jornada='JM', nombre='X')
        self.assertEqual(a.periodo, Periodo.actual())

    def test_definitivas_por_periodo_y_anio(self):
        from datetime import date
        from estudiantes.models import NotaActividad, RegistroPlanilla
        from estudiantes.periodos import calcular_periodos
        NotaActividad.objects.create(estudiante=self.est, actividad=self._act(self.p1), valor=Decimal('4.0'))
        NotaActividad.objects.create(estudiante=self.est, actividad=self._act(self.p2), valor=Decimal('3.0'))
        RegistroPlanilla.objects.create(estudiante=self.est, fecha=date(2026, 6, 2), bloque=1, estado='R',
                                        puntos_aplicados=Decimal('-1'))
        _, datos = calcular_periodos([self.est.id], 2026)
        d = datos[self.est.id]
        self.assertEqual(d['periodos'][self.p1.id]['definitiva'], Decimal('4.00'))
        self.assertEqual(d['periodos'][self.p2.id]['definitiva'], Decimal('2.00'))   # 3.0 - 1
        self.assertIsNone(d['periodos'][self.p3.id]['definitiva'])
        self.assertEqual(d['anio'], Decimal('3.00'))

    def test_notas_del_docente_se_separan_por_periodo(self):
        from estudiantes.models import NotaActividad
        a1, a2 = self._act(self.p1, 'A1'), self._act(self.p2, 'A2')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.client.post(reverse('notas'), {'periodo': self.p1.id, f'nota_{self.est.id}_{a1.id}': '4'})
        self.client.post(reverse('notas'), {'periodo': self.p2.id, f'nota_{self.est.id}_{a2.id}': '2,5'})
        self.assertEqual(NotaActividad.objects.get(actividad=a1).valor, Decimal('4.00'))
        self.assertEqual(NotaActividad.objects.get(actividad=a2).valor, Decimal('2.50'))
        r = self.client.get(reverse('notas'), {'periodo': self.p2.id})
        self.assertEqual([a.nombre for a in r.context['actividades']], ['A2'])
        self.assertEqual(len(r.context['periodos_anio']), 3)

    def test_crear_actividad_va_al_periodo_elegido(self):
        from estudiantes.models import Actividad
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.client.post(reverse('notas'), {'periodo': self.p3.id, 'nueva_actividad': 'Proyecto'})
        self.assertEqual(Actividad.objects.get(nombre='Proyecto').periodo, self.p3)

    def test_exportar_incluye_hoja_del_anio(self):
        import io, openpyxl
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        r = self.client.get(reverse('exportar_planilla'), {'periodo': self.p1.id})
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertIn('Año 2026', wb.sheetnames)

    def test_estudiante_ve_mi_proceso(self):
        from datetime import date
        from unittest import mock
        from estudiantes.models import NotaActividad
        NotaActividad.objects.create(estudiante=self.est, actividad=self._act(self.p1), valor=Decimal('4.5'))
        self.client.login(username=self.est.usuario.username, password=self.est.documento)
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 6, 10)):
            r = self.client.get(reverse('mi_proceso'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['actual'].numero, 2)
        self.assertEqual(r.context['anual']['valor'], 4.5)
        self.assertEqual(r.context['anual']['con_nota'], 1)
        self.assertContains(r, 'Todo el año')

    def test_no_estudiantes_no_entran_a_mi_proceso(self):
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        r = self.client.get(reverse('mi_proceso'))
        self.assertRedirects(r, reverse('inicio'), fetch_redirect_response=False)


class PorcentajesTests(BaseTestCase):
    def setUp(self):
        from datetime import date
        from estudiantes.models import Periodo
        Periodo.asegurar_anio(date.today().year)
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.est = self.crear_estudiante_con_acceso(linea='ROB', jornada='JM')

    def _nota(self, nombre, tipo, valor):
        from estudiantes.models import Actividad, NotaActividad
        a = Actividad.objects.create(linea='ROB', jornada='JM', nombre=nombre, tipo=tipo)
        NotaActividad.objects.create(estudiante=self.est, actividad=a, valor=Decimal(valor))
        return a

    def test_defecto_70_20_10(self):
        from estudiantes.models import ConfiguracionPorcentajes
        self.assertEqual(ConfiguracionPorcentajes.obtener().por_tipo(),
                         {'GEN': Decimal('70'), 'EVA': Decimal('20'), 'AUT': Decimal('10')})

    def test_ponderacion_completa(self):
        from estudiantes.periodos import promedio_ponderado
        prom, comp = promedio_ponderado(
            {'GEN': [Decimal('4'), Decimal('3')], 'EVA': [Decimal('5')], 'AUT': [Decimal('2')]},
            {'GEN': Decimal('70'), 'EVA': Decimal('20'), 'AUT': Decimal('10')})
        # 3.5*0.7 + 5*0.2 + 2*0.1 = 2.45 + 1.0 + 0.2
        self.assertEqual(prom, Decimal('3.65'))

    def test_solo_generales_equivale_al_promedio_simple(self):
        from estudiantes.periodos import promedio_ponderado
        prom, _ = promedio_ponderado({'GEN': [Decimal('4'), Decimal('3')]},
                                     {'GEN': Decimal('70'), 'EVA': Decimal('20'), 'AUT': Decimal('10')})
        self.assertEqual(prom, Decimal('3.50'))

    def test_si_falta_un_tipo_se_reparte_entre_los_que_hay(self):
        from estudiantes.periodos import promedio_ponderado
        prom, _ = promedio_ponderado({'GEN': [Decimal('4')], 'EVA': [Decimal('2')]},
                                     {'GEN': Decimal('70'), 'EVA': Decimal('20'), 'AUT': Decimal('10')})
        self.assertEqual(prom, Decimal('3.56'))   # (4*70 + 2*20) / 90

    def test_cambiar_porcentajes_cambia_la_definitiva(self):
        from estudiantes.models import ConfiguracionPorcentajes
        from estudiantes.periodos import calcular_periodos
        from datetime import date
        self._nota('G', 'GEN', '4')
        self._nota('E', 'EVA', '2')
        cfg = ConfiguracionPorcentajes.obtener()
        cfg.generales, cfg.evaluacion, cfg.autoevaluacion = Decimal('50'), Decimal('50'), Decimal('0')
        cfg.save()
        periodos, datos = calcular_periodos([self.est.id], date.today().year)
        actual = next(p for p in periodos if p.fecha_inicio <= date.today() <= p.fecha_fin)
        self.assertEqual(datos[self.est.id]['periodos'][actual.id]['promedio'], Decimal('3.00'))

    def test_validacion_exige_suma_100(self):
        from django.core.exceptions import ValidationError
        from estudiantes.models import ConfiguracionPorcentajes
        cfg = ConfiguracionPorcentajes(generales=Decimal('60'), evaluacion=Decimal('20'), autoevaluacion=Decimal('10'))
        with self.assertRaises(ValidationError):
            cfg.full_clean()

    def test_docente_crea_evaluacion_y_se_refleja_en_notas(self):
        from estudiantes.models import Actividad
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.client.post(reverse('notas'), {'nueva_actividad': 'Evaluación P3', 'tipo_actividad': 'EVA'})
        a = Actividad.objects.get(nombre='Evaluación P3')
        self.assertEqual(a.tipo, 'EVA')
        self.client.post(reverse('notas'), {f'nota_{self.est.id}_{a.id}': '4'})
        g = self._nota('Taller', 'GEN', '2')
        r = self.client.get(reverse('notas'))
        fila = r.context['resumen'][self.est.id]
        self.assertEqual(fila['promedio'], Decimal('2.44'))   # (2*70 + 4*20) / 90

    def test_tipo_invalido_cae_en_general(self):
        from estudiantes.models import Actividad
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.client.post(reverse('notas'), {'nueva_actividad': 'Rara', 'tipo_actividad': 'XXX'})
        self.assertEqual(Actividad.objects.get(nombre='Rara').tipo, 'GEN')
