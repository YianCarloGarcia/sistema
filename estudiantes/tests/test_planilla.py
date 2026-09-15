from django.urls import reverse

from estudiantes.models import RegistroPlanilla
from .base import CLAVE_PRUEBA, BaseTestCase


class PlanillaTests(BaseTestCase):

    def setUp(self):
        self.docente = self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.estudiante = self.crear_estudiante(curso='1101', jornada='JM', linea='ROB')

    def _guardar(self, estados, fecha='2026-08-10', bloque='1'):
        datos = {'linea': 'ROB', 'jornada': 'JM', 'grado': '', 'fecha': fecha, 'bloque': bloque}
        return self.client.post(reverse('planilla'), {
            **datos,
            f'estado_{self.estudiante.id}': estados,
        })

    def test_registrar_un_item(self):
        self._guardar(['R'])
        estados = set(RegistroPlanilla.objects.filter(
            estudiante=self.estudiante, fecha='2026-08-10', bloque=1
        ).values_list('estado', flat=True))
        self.assertEqual(estados, {'R'})

    def test_modificar_registro_existente(self):
        self._guardar(['R'])
        self._guardar(['U'])  # reemplaza R por U en el mismo bloque
        estados = set(RegistroPlanilla.objects.filter(
            estudiante=self.estudiante, fecha='2026-08-10', bloque=1
        ).values_list('estado', flat=True))
        self.assertEqual(estados, {'U'})

    def test_varios_items_en_el_mismo_bloque(self):
        self._guardar(['R', 'U'])
        estados = set(RegistroPlanilla.objects.filter(
            estudiante=self.estudiante, fecha='2026-08-10', bloque=1
        ).values_list('estado', flat=True))
        self.assertEqual(estados, {'R', 'U'})

    def test_falla_bloquea_los_demas_items_salvo_excusa(self):
        self._guardar(['F', 'R', 'U'])
        estados = set(RegistroPlanilla.objects.filter(
            estudiante=self.estudiante, fecha='2026-08-10', bloque=1
        ).values_list('estado', flat=True))
        self.assertEqual(estados, {'F'})  # R y U quedan descartados

    def test_falla_mas_excusa_conviven_y_no_restan_puntos(self):
        self._guardar(['F', 'EX'])
        estados = set(RegistroPlanilla.objects.filter(
            estudiante=self.estudiante, fecha='2026-08-10', bloque=1
        ).values_list('estado', flat=True))
        self.assertEqual(estados, {'F', 'EX'})

        puntos = RegistroPlanilla.calcular_puntos_por_estudiante(
            RegistroPlanilla.objects.filter(estudiante=self.estudiante)
            .values('estudiante_id', 'fecha', 'bloque', 'estado', 'puntos_aplicados')
        )
        self.assertEqual(puntos.get(self.estudiante.id, 0), 0)

    def test_falla_sin_excusa_si_resta_puntos(self):
        self._guardar(['F'])
        puntos = RegistroPlanilla.calcular_puntos_por_estudiante(
            RegistroPlanilla.objects.filter(estudiante=self.estudiante)
            .values('estudiante_id', 'fecha', 'bloque', 'estado', 'puntos_aplicados')
        )
        self.assertEqual(puntos.get(self.estudiante.id, 0), -1)

    def test_desmarcar_todo_borra_el_registro(self):
        self._guardar(['R'])
        self._guardar([])  # no se envía ningún estado_<id>
        existe = RegistroPlanilla.objects.filter(
            estudiante=self.estudiante, fecha='2026-08-10', bloque=1
        ).exists()
        self.assertFalse(existe)


class PlanillaPermisosGrupoTests(BaseTestCase):

    def setUp(self):
        self.crear_docente(username='docente_rob', linea='ROB', jornada='JM')
        self.crear_docente(username='docente_tps', linea='TPS', jornada='JM')
        self.estudiante_rob = self.crear_estudiante(curso='1101', jornada='JM', linea='ROB')
        self.estudiante_tps = self.crear_estudiante(curso='1101', jornada='JM', linea='TPS')

    def test_docente_no_puede_registrar_en_grupo_ajeno(self):
        self.client.login(username='docente_rob', password=CLAVE_PRUEBA)
        # Intenta registrar directamente sobre la línea TPS, que no es la suya
        self.client.post(reverse('planilla'), {
            'linea': 'TPS', 'jornada': 'JM', 'grado': '', 'fecha': '2026-08-11', 'bloque': '1',
            f'estado_{self.estudiante_tps.id}': ['F'],
        })
        # Como el servidor ignora el 'linea' recibido y usa el de su perfil, el
        # estudiante de TPS no debe recibir ningún registro
        self.assertFalse(
            RegistroPlanilla.objects.filter(estudiante=self.estudiante_tps).exists()
        )


class PuntosHistoricosTests(BaseTestCase):
    """Punto 27: cambiar la configuración de puntos hoy no debe alterar
    retroactivamente las definitivas ya calculadas de meses anteriores."""

    def setUp(self):
        self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.estudiante = self.crear_estudiante(curso='1101', jornada='JM', linea='ROB')

    def test_cambiar_configuracion_no_afecta_registro_ya_guardado(self):
        from estudiantes.models import ConfiguracionPuntos

        self.client.post(reverse('planilla'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': '', 'fecha': '2026-08-10', 'bloque': '1',
            f'estado_{self.estudiante.id}': ['F'],
        })
        registro = RegistroPlanilla.objects.get(estudiante=self.estudiante, fecha='2026-08-10', bloque=1)
        self.assertEqual(registro.puntos_aplicados, -1)

        # El directivo cambia la configuración de "Falla" de -1 a -9
        ConfiguracionPuntos.objects.filter(estado='F').update(puntos=-9)

        registro.refresh_from_db()
        self.assertEqual(registro.puntos_aplicados, -1)  # el registro viejo no se mueve

        puntos_totales = RegistroPlanilla.calcular_puntos_por_estudiante(
            RegistroPlanilla.objects.filter(estudiante=self.estudiante)
            .values('estudiante_id', 'fecha', 'bloque', 'estado', 'puntos_aplicados')
        )
        self.assertEqual(puntos_totales.get(self.estudiante.id, 0), -1)

        # Un registro NUEVO sí usa el valor recién configurado
        self.client.post(reverse('planilla'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': '', 'fecha': '2026-08-11', 'bloque': '1',
            f'estado_{self.estudiante.id}': ['F'],
        })
        registro_nuevo = RegistroPlanilla.objects.get(estudiante=self.estudiante, fecha='2026-08-11', bloque=1)
        self.assertEqual(registro_nuevo.puntos_aplicados, -9)

    def test_ajustar_desde_historial_recalcula_con_la_configuracion_vigente(self):
        from estudiantes.models import ConfiguracionPuntos

        self.client.post(reverse('planilla'), {
            'linea': 'ROB', 'jornada': 'JM', 'grado': '', 'fecha': '2026-08-10', 'bloque': '1',
            f'estado_{self.estudiante.id}': ['R'],
        })
        registro = RegistroPlanilla.objects.get(estudiante=self.estudiante, fecha='2026-08-10', bloque=1)

        ConfiguracionPuntos.objects.filter(estado='U').update(puntos=-7)
        self.client.post(reverse('historial_planilla'), {
            'linea': 'ROB', 'jornada': 'JM', 'registro_id': registro.id,
            'nuevo_estado': 'U', 'ajustar': '1',
        })
        registro.refresh_from_db()
        self.assertEqual(registro.estado, 'U')
        self.assertEqual(registro.puntos_aplicados, -7)


class RendimientoPlanillaTests(BaseTestCase):
    """Puntos 10 y 11: guardar la planilla y las notas de un grupo completo no debe
    generar una consulta a la base de datos por cada estudiante."""

    def setUp(self):
        self.crear_docente(linea='ROB', jornada='JM')
        self.client.login(username='docente1', password=CLAVE_PRUEBA)
        self.estudiantes = [
            self.crear_estudiante(curso='1101', jornada='JM', linea='ROB') for _ in range(15)
        ]

    def test_guardar_planilla_de_15_estudiantes_usa_pocas_consultas(self):
        datos = {'linea': 'ROB', 'jornada': 'JM', 'grado': '', 'fecha': '2026-08-12', 'bloque': '1'}
        for est in self.estudiantes:
            datos[f'estado_{est.id}'] = ['R']

        # Con el bucle antiguo (una consulta de lectura + una de escritura por
        # estudiante) esto habría sido 30+ consultas solo para guardar. Con las
        # operaciones en bloque debe mantenerse muy por debajo de eso.
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as contexto:
            self.client.post(reverse('planilla'), datos)
        self.assertLess(len(contexto), 15, f"Se ejecutaron {len(contexto)} consultas guardando 15 estudiantes")

        self.assertEqual(RegistroPlanilla.objects.filter(estado='R').count(), 15)

    def test_guardar_notas_de_15_estudiantes_usa_pocas_consultas(self):
        from estudiantes.models import Actividad
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        actividad = Actividad.objects.create(linea='ROB', jornada='JM', nombre='Taller', orden=1)
        datos = {'linea': 'ROB', 'jornada': 'JM', 'grado': ''}
        for est in self.estudiantes:
            datos[f'nota_{est.id}_{actividad.id}'] = '4.5'

        with CaptureQueriesContext(connection) as contexto:
            self.client.post(reverse('notas'), datos)
        self.assertLess(len(contexto), 15, f"Se ejecutaron {len(contexto)} consultas guardando 15 notas")

        from estudiantes.models import NotaActividad
        self.assertEqual(NotaActividad.objects.filter(actividad=actividad).count(), 15)
