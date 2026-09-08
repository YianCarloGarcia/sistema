"""
Utilidades compartidas por toda la suite de pruebas: crear estudiantes, docentes,
directivos y cuentas de estudiante sin repetir el mismo boilerplate en cada archivo.
"""
from django.contrib.auth.models import User, Group
from django.test import TestCase

from estudiantes.models import DocentePerfil, Estudiante

CLAVE_PRUEBA = 'ClaveDePrueba123'


class BaseTestCase(TestCase):

    contador_documento = 1000000000

    def _siguiente_documento(self):
        BaseTestCase.contador_documento += 1
        return str(BaseTestCase.contador_documento)

    def crear_estudiante(self, documento=None, apellidos='Pérez', nombres='Juan',
                          curso='1101', jornada='JM', linea='ROB', **extra):
        return Estudiante.objects.create(
            documento=documento or self._siguiente_documento(),
            apellidos=apellidos,
            nombres=nombres,
            curso=curso,
            jornada=jornada,
            linea=linea,
            **extra,
        )

    def crear_directivo(self, username='directivo1', password=CLAVE_PRUEBA, superuser=False):
        if superuser:
            user = User.objects.create_superuser(username=username, email='', password=password)
        else:
            user = User.objects.create_user(username=username, password=password)
            grupo, _ = Group.objects.get_or_create(name='directivo')
            user.groups.add(grupo)
        return user

    def crear_docente(self, username='docente1', password=CLAVE_PRUEBA, linea='ROB', jornada='JM'):
        user = User.objects.create_user(username=username, password=password)
        grupo, _ = Group.objects.get_or_create(name='docente')
        user.groups.add(grupo)
        DocentePerfil.objects.create(usuario=user, linea=linea, jornada=jornada)
        return user

    def crear_estudiante_con_acceso(self, documento=None, password=None, debe_cambiar_clave=False, **extra):
        estudiante = self.crear_estudiante(documento=documento, **extra)
        password = password or estudiante.documento
        user = User.objects.create_user(username=f'est{estudiante.documento}', password=password)
        grupo, _ = Group.objects.get_or_create(name='estudiante')
        user.groups.add(grupo)
        estudiante.usuario = user
        estudiante.debe_cambiar_clave = debe_cambiar_clave
        estudiante.save()
        return estudiante
