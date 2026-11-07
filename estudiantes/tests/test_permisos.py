from django.urls import reverse

from .base import CLAVE_PRUEBA, BaseTestCase


class PermisosEstudianteTests(BaseTestCase):
    """Un estudiante solo debe poder ver su propio historial, nunca el panel interno."""

    def setUp(self):
        self.estudiante = self.crear_estudiante_con_acceso()
        self.client.login(username=self.estudiante.usuario.username, password=self.estudiante.documento)

    def test_no_puede_ver_listado_de_estudiantes(self):
        respuesta = self.client.get(reverse('estudiantes'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('mi_historial'), respuesta.url)

    def test_no_puede_acceder_al_escaner(self):
        respuesta = self.client.get(reverse('escaner'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('mi_historial'), respuesta.url)

    def test_no_puede_acceder_a_planilla_ni_notas(self):
        for nombre_url in ['planilla', 'notas', 'historial_planilla']:
            respuesta = self.client.get(reverse(nombre_url))
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn(reverse('mi_historial'), respuesta.url)

    def test_no_puede_acceder_a_gestion_de_usuarios(self):
        respuesta = self.client.get(reverse('lista_usuarios'), follow=True)
        self.assertEqual(respuesta.status_code, 200)
        # solo_directivo redirige a inicio, no muestra la lista de usuarios
        self.assertTemplateNotUsed(respuesta, 'usuarios/lista.html')

    def test_si_puede_ver_su_propio_historial(self):
        respuesta = self.client.get(reverse('mi_historial'))
        self.assertEqual(respuesta.status_code, 200)


class PermisosDocenteTests(BaseTestCase):
    """Un docente administra la planilla/notas de su línea, pero no la ficha de estudiantes
    ni la gestión de usuarios, y no puede salirse de su propia línea/jornada."""

    def setUp(self):
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.estudiante_propio = self.crear_estudiante(curso='1101', jornada='JM', linea='ROB')
        self.estudiante_ajeno = self.crear_estudiante(curso='1101', jornada='JM', linea='TPS')

    def test_puede_ver_el_listado_de_estudiantes_de_solo_lectura(self):
        """
        Comportamiento ACTUAL: 'estudiantes', 'detalle' y 'escaner' solo usan
        @bloquear_estudiantes (que únicamente bloquea cuentas de estudiante), no
        @solo_directivo. Un docente autenticado sí puede ver el listado y el
        detalle de cualquier estudiante del colegio, no solo los de su línea.
        Este test documenta el comportamiento real para detectar cualquier cambio;
        NO es una recomendación de diseño (ver punto 9 del análisis de seguridad:
        conviene decidir si esto debe restringirse a la línea del docente).
        """
        respuesta = self.client.get(reverse('estudiantes'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'estudiantes/index.html')

    def test_no_puede_crear_estudiantes(self):
        respuesta = self.client.get(reverse('crear'), follow=True)
        self.assertTemplateNotUsed(respuesta, 'estudiantes/crear.html')

    def test_no_puede_editar_estudiantes(self):
        respuesta = self.client.get(reverse('editar', args=[self.estudiante_propio.id]), follow=True)
        self.assertTemplateNotUsed(respuesta, 'estudiantes/editar.html')

    def test_no_puede_eliminar_estudiantes(self):
        respuesta = self.client.post(reverse('eliminar', args=[self.estudiante_propio.id]), follow=True)
        self.estudiante_propio.refresh_from_db()  # no debe lanzar DoesNotExist
        self.assertIsNotNone(self.estudiante_propio.id)

    def test_no_puede_gestionar_usuarios(self):
        respuesta = self.client.get(reverse('lista_usuarios'), follow=True)
        self.assertTemplateNotUsed(respuesta, 'usuarios/lista.html')

    def test_planilla_solo_muestra_su_propia_linea_y_jornada(self):
        respuesta = self.client.get(reverse('planilla'))
        ids_visibles = {e.id for e in respuesta.context['estudiantes_grupo']}
        self.assertIn(self.estudiante_propio.id, ids_visibles)
        self.assertNotIn(self.estudiante_ajeno.id, ids_visibles)

    def test_no_puede_forzar_otra_linea_por_query_string(self):
        """Aunque intente pasar ?linea=TPS por la URL, un docente (no directivo) debe
        seguir viendo únicamente el grupo que tiene asignado."""
        respuesta = self.client.get(reverse('planilla'), {'linea': 'TPS', 'jornada': 'JM'})
        ids_visibles = {e.id for e in respuesta.context['estudiantes_grupo']}
        self.assertIn(self.estudiante_propio.id, ids_visibles)
        self.assertNotIn(self.estudiante_ajeno.id, ids_visibles)

    def test_no_puede_ajustar_registro_de_otra_linea_por_historial(self):
        from estudiantes.models import RegistroPlanilla
        registro_ajeno = RegistroPlanilla.objects.create(
            estudiante=self.estudiante_ajeno, fecha='2026-08-01', bloque=1, estado='F',
        )
        self.client.post(reverse('historial_planilla'), {
            'registro_id': registro_ajeno.id, 'eliminar': '1',
            'linea': 'ROB', 'jornada': 'JM',  # intenta colarse con su propia línea
        })
        self.assertTrue(RegistroPlanilla.objects.filter(id=registro_ajeno.id).exists())


class PermisosDirectivoTests(BaseTestCase):
    """Un directivo sí tiene acceso administrativo completo."""

    def setUp(self):
        self.directivo = self.crear_directivo()
        self.client.login(username='directivo1', password=CLAVE_PRUEBA)

    def test_puede_ver_listado_de_estudiantes(self):
        respuesta = self.client.get(reverse('estudiantes'))
        self.assertEqual(respuesta.status_code, 200)

    def test_puede_crear_estudiante(self):
        respuesta = self.client.get(reverse('crear'))
        self.assertEqual(respuesta.status_code, 200)

    def test_puede_gestionar_usuarios(self):
        respuesta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(respuesta.status_code, 200)

    def test_puede_elegir_cualquier_grupo_en_planilla(self):
        est_rob = self.crear_estudiante(curso='1101', jornada='JM', linea='ROB')
        est_tps = self.crear_estudiante(curso='1101', jornada='JM', linea='TPS')

        respuesta_rob = self.client.get(reverse('planilla'), {'linea': 'ROB', 'jornada': 'JM'})
        ids_rob = {e.id for e in respuesta_rob.context['estudiantes_grupo']}
        self.assertIn(est_rob.id, ids_rob)
        self.assertNotIn(est_tps.id, ids_rob)

        respuesta_tps = self.client.get(reverse('planilla'), {'linea': 'TPS', 'jornada': 'JM'})
        ids_tps = {e.id for e in respuesta_tps.context['estudiantes_grupo']}
        self.assertIn(est_tps.id, ids_tps)
        self.assertNotIn(est_rob.id, ids_tps)


class AsignacionLineaDocenteTests(BaseTestCase):
    def test_perfil_creado_fuera_del_panel_da_acceso_y_grupo(self):
        from django.contrib.auth.models import User
        from estudiantes.models import DocentePerfil
        u = User.objects.create_user('adm', 'a@b.co', CLAVE_PRUEBA)   # como desde el admin de Django
        DocentePerfil.objects.create(usuario=u, linea='ROB', jornada='JM')
        self.assertTrue(u.groups.filter(name='docente').exists())
        self.client.login(username='adm', password=CLAVE_PRUEBA)
        for nombre in ('planilla', 'notas', 'actividad_linea'):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_docente_sin_linea_ve_aviso_en_inicio(self):
        from django.contrib.auth.models import User, Group
        u = User.objects.create_user('sinlinea', 'a@b.co', CLAVE_PRUEBA)
        u.groups.add(Group.objects.get_or_create(name='docente')[0])
        self.client.login(username='sinlinea', password=CLAVE_PRUEBA)
        r = self.client.get(reverse('inicio'))
        self.assertContains(r, 'aún no tiene línea asignada')
        self.assertEqual(self.client.get(reverse('notas')).status_code, 302)

    def test_docente_con_linea_solo_ve_su_grupo(self):
        self.crear_docente(linea='ROB', jornada='JM')
        propio = self.crear_estudiante(linea='ROB', jornada='JM', apellidos='Propio')
        ajeno = self.crear_estudiante(linea='BIO', jornada='JM', apellidos='Ajeno')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        r = self.client.get(reverse('notas'), {'linea': 'BIO', 'jornada': 'JM'})
        ids = [e.id for e in r.context['estudiantes_grupo']]
        self.assertIn(propio.id, ids)
        self.assertNotIn(ajeno.id, ids)
        self.assertContains(self.client.get(reverse('inicio')), reverse('planilla'))

    def test_admin_de_usuarios_permite_asignar_linea(self):
        from django.contrib.auth.models import User
        User.objects.create_superuser('root', 'r@b.co', CLAVE_PRUEBA)
        self.client.login(username='root', password=CLAVE_PRUEBA)
        self.assertEqual(self.client.get('/admin/auth/user/add/').status_code, 200)
