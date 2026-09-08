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
            .values('estudiante_id', 'fecha', 'bloque', 'estado')
        )
        self.assertEqual(puntos.get(self.estudiante.id, 0), 0)

    def test_falla_sin_excusa_si_resta_puntos(self):
        self._guardar(['F'])
        puntos = RegistroPlanilla.calcular_puntos_por_estudiante(
            RegistroPlanilla.objects.filter(estudiante=self.estudiante)
            .values('estudiante_id', 'fecha', 'bloque', 'estado')
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
