from django.db import models
from django.utils import timezone
from django.conf import settings

# Create your models here.
class Estudiante(models.Model):
    id = models.AutoField(primary_key=True)
    
    JORNADA = [
        ('JM', 'Jornada Mañana'),
        ('JT', 'Jornada Tarde'),
    ]
    TIPOS_DOCUMENTO = [
        ('CC', 'Cédula de Ciudadanía'),
        ('TI', 'Tarjeta de Identidad'),
        ('PP', 'Permito de Protección'),
        ('OT', 'Otro'),
    ]
    LINEA_MEDIA = [
        ('AA', 'Asistencia Administrativa'),
        ('ISERC', 'Instalaciones eléctricas'),
        ('TPS', 'Programación de Software'),
        ('COM', 'Comunicación y medios audiovisuales'),
        ('ROB', 'Robótica'),
        ('BIO', 'Biotecnología'),
        ('DIS', 'Diseño multimedia'),
        ('OT', 'Otro'),
    ]
    jornada = models.CharField(max_length=50, choices=JORNADA, verbose_name="Jornada", default='JM')
    tipo = models.CharField(max_length=2,choices=TIPOS_DOCUMENTO, verbose_name="Tipo", default='CC')
    documento = models.CharField(max_length=20, verbose_name="Documento")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    curso = models.CharField(max_length=100, verbose_name="Curso")
    linea = models.CharField(max_length=50,choices=LINEA_MEDIA, verbose_name="Línea", default='OT')
    celular = models.CharField(max_length=20, verbose_name="Celular", null=True, blank=True)
    email = models.EmailField(max_length=100, verbose_name="Email", null=True, blank=True)
    acudiente = models.CharField(max_length=100, verbose_name="Acudiente", null=True, blank=True)
    parentesco = models.CharField(max_length=50, verbose_name="Parentesco Acudiente", null=True, blank=True)
    tel_acudiente = models.CharField(max_length=20, verbose_name="Teléfono Acudiente", null=True, blank=True)
    tel2_acudiente = models.CharField(max_length=20, verbose_name="Teléfono 2 Acudiente", null=True, blank=True)
    direccion = models.CharField(max_length=200, verbose_name="Dirección", null=True, blank=True)
    ocupacion_acudiente = models.CharField(max_length=100, verbose_name="Ocupación Acudiente", null=True, blank=True)
    eps = models.CharField(max_length=100, verbose_name="EPS", null=True, blank=True)
    observaciones = models.TextField(verbose_name="Observaciones", null=True, blank=True)
    foto = models.ImageField(upload_to='fotos/', null=True, blank=True)

    DEPENDENCIA_PRACTICA = [
        ('COORD_PRIM', 'Coordinación Primaria'),
        ('COORD_BACH', 'Coordinación Bachillerato'),
        ('ORIENTACION', 'Orientación'),
        ('SECRETARIA', 'Secretaría'),
        ('BIBLIOTECA', 'Biblioteca'),
        ('COORD_MED', 'Coordinación de Media'),
        ('OTRO', 'Otro'),
    ]
    en_practica = models.BooleanField(default=False, verbose_name="¿Está haciendo práctica?")
    fecha_inicio_practica = models.DateField(verbose_name="Fecha de inicio de práctica", null=True, blank=True)
    dependencia_practica = models.CharField(max_length=20, choices=DEPENDENCIA_PRACTICA, verbose_name="Dependencia de práctica", null=True, blank=True)

    # Cuenta de acceso individual del estudiante (usuario y contraseña propios)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='estudiante_perfil',
        verbose_name='Usuario de acceso',
    )
    debe_cambiar_clave = models.BooleanField(
        default=False,
        verbose_name='Debe cambiar contraseña al ingresar',
    )

    
    # mostrrar datos en el admin
    def __str__(self):
        return f"{self.apellidos}, {self.nombres}"
    # Borrar imagen al eliminar registro
    def delete(self, using=None, keep_parents=False):
        if self.foto and self.foto.name:
            try:
                self.foto.storage.delete(self.foto.name)
            except Exception:
                pass
        super().delete()

class Asistencia(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)

    TIPO_REGISTRO = [
        ('ALM', 'Almuerzo'),
        ('TAR', 'Llegada tarde'),
        ('UNI', 'Porte de uniforme'),
        ('ASI', 'Asistencia a clase'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_REGISTRO, default='ALM')

    def __str__(self):
        return f"{self.estudiante} - {self.fecha} - {self.hora}"


class DocentePerfil(models.Model):
    """Vincula la cuenta de un docente con el grupo (línea + jornada + curso) que le fue asignado."""
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='docente_perfil',
        verbose_name='Usuario',
    )
    linea = models.CharField(max_length=50, choices=Estudiante.LINEA_MEDIA, verbose_name='Línea')
    jornada = models.CharField(max_length=50, choices=Estudiante.JORNADA, verbose_name='Jornada')
    curso = models.CharField(max_length=100, verbose_name='Curso')

    class Meta:
        verbose_name = 'Docente — grupo asignado'
        verbose_name_plural = 'Docentes — grupos asignados'

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} — {self.curso} ({self.get_linea_display()}, {self.get_jornada_display()})"


class RegistroPlanilla(models.Model):
    """Registro diario de la planilla del docente: un estado por estudiante, fecha y bloque de clase."""
    ESTADOS = [
        ('F',  'Falla'),
        ('A',  'Asistió'),
        ('R',  'Llegada tarde'),
        ('E',  'Evasión de clase'),
        ('EX', 'Excusa justificada'),
        ('U',  'Uniforme incompleto'),
    ]
    BLOQUES = [
        (1, 'Bloque 1'),
        (2, 'Bloque 2'),
    ]
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='registros_planilla')
    fecha = models.DateField(verbose_name='Fecha')
    bloque = models.PositiveSmallIntegerField(choices=BLOQUES, default=1, verbose_name='Bloque')
    estado = models.CharField(max_length=2, choices=ESTADOS, verbose_name='Estado')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registros_planilla_creados',
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['estudiante', 'fecha', 'bloque'], name='unico_estudiante_fecha_bloque')
        ]
        verbose_name = 'Registro de planilla'
        verbose_name_plural = 'Registros de planilla'

    def __str__(self):
        return f"{self.estudiante} — {self.fecha} B{self.bloque}: {self.estado}"


    