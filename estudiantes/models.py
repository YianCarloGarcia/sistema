from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

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
    documento = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="Documento")
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
    """Vincula la cuenta de un docente con la línea + jornada que le fue asignada."""
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='docente_perfil',
        verbose_name='Usuario',
    )
    linea = models.CharField(max_length=50, choices=Estudiante.LINEA_MEDIA, verbose_name='Línea')
    jornada = models.CharField(max_length=50, choices=Estudiante.JORNADA, verbose_name='Jornada')

    class Meta:
        verbose_name = 'Docente — grupo asignado'
        verbose_name_plural = 'Docentes — grupos asignados'

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} — {self.get_linea_display()} ({self.get_jornada_display()})"


class RegistroPlanilla(models.Model):
    """Registro diario de la planilla del docente: uno o más ítems (estado) por estudiante,
    fecha y bloque de clase. Varios ítems pueden coexistir en el mismo bloque (por ejemplo,
    llegada tarde + uniforme incompleto). La única excepción es la Falla (F): al marcarla,
    ningún otro ítem puede coexistir en ese bloque salvo la Excusa justificada (EX), que la
    remedia (ver `calcular_puntos_por_estudiante`)."""
    ESTADOS = [
        ('F',  'Falla'),
        ('A',  'Asistió'),
        ('R',  'Llegada tarde'),
        ('E',  'Evasión de clase'),
        ('EX', 'Excusa justificada'),
        ('U',  'Uniforme incompleto'),
    ]
    # Puntos por defecto que suma/resta cada estado a la nota definitiva del estudiante.
    # La excusa justificada (EX) anula la sanción: no resta puntos.
    # Estos son solo el respaldo inicial: el valor real y editable vive en ConfiguracionPuntos
    # (administrable desde el admin de Django) y se usa siempre que exista.
    PUNTOS_POR_DEFECTO = {
        'F':  Decimal('-1'),
        'A':  Decimal('0'),
        'R':  Decimal('-1'),
        'E':  Decimal('-5'),
        'EX': Decimal('0'),
        'U':  Decimal('-1'),
    }
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
            models.UniqueConstraint(fields=['estudiante', 'fecha', 'bloque', 'estado'], name='unico_estudiante_fecha_bloque_estado')
        ]
        verbose_name = 'Registro de planilla'
        verbose_name_plural = 'Registros de planilla'

    def __str__(self):
        return f"{self.estudiante} — {self.fecha} B{self.bloque}: {self.estado}"

    @classmethod
    def obtener_puntos(cls):
        """Mapa estado -> puntos, tomando lo configurado en el admin (ConfiguracionPuntos)
        y completando con los valores por defecto para cualquier estado sin configurar."""
        configurados = dict(ConfiguracionPuntos.objects.values_list('estado', 'puntos'))
        resultado = dict(cls.PUNTOS_POR_DEFECTO)
        resultado.update(configurados)
        return resultado

    @classmethod
    def calcular_puntos_por_estudiante(cls, registros):
        """Agrupa `registros` (queryset, iterable de instancias, o de dicts con las claves
        estudiante_id/fecha/bloque/estado) por bloque de clase y devuelve {estudiante_id: puntos}.

        Varios ítems pueden coexistir en un mismo bloque y sus puntos se suman (ej: llegada
        tarde + uniforme incompleto). La única excepción: si en el mismo bloque coinciden
        Falla (F) y Excusa justificada (EX), la excusa remedia la falla y ese bloque no
        resta puntos en absoluto."""
        puntos_config = cls.obtener_puntos()
        bloques = {}
        for r in registros:
            if isinstance(r, dict):
                clave = (r['estudiante_id'], r['fecha'], r['bloque'])
                estado = r['estado']
            else:
                clave = (r.estudiante_id, r.fecha, r.bloque)
                estado = r.estado
            bloques.setdefault(clave, set()).add(estado)

        puntos_por_estudiante = {}
        for (estudiante_id, fecha, bloque), estados in bloques.items():
            if 'F' in estados and 'EX' in estados:
                puntos_bloque = 0
            else:
                puntos_bloque = sum(puntos_config.get(e, 0) for e in estados)
            puntos_por_estudiante[estudiante_id] = puntos_por_estudiante.get(estudiante_id, 0) + puntos_bloque
        return puntos_por_estudiante

    @property
    def puntos(self):
        return self.obtener_puntos().get(self.estado, 0)


class ConfiguracionPuntos(models.Model):
    """Puntos que suma o resta cada estado de asistencia a la nota definitiva.
    Editable desde el admin de Django: el cambio se refleja de inmediato en toda planilla,
    notas y reporte exportado."""
    estado = models.CharField(max_length=2, choices=RegistroPlanilla.ESTADOS, unique=True, verbose_name='Estado')
    puntos = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Puntos (use un número negativo para descontar; admite decimales, ej: -0.5)',
    )

    class Meta:
        verbose_name = 'Puntos por estado de asistencia'
        verbose_name_plural = 'Configuración de puntos por asistencia'
        ordering = ['estado']

    def __str__(self):
        return f"{self.get_estado_display()}: {self.puntos:+.2f}"


class Actividad(models.Model):
    """Actividad calificable definida por el docente para su línea/jornada (equivalente a las
    columnas D:O 'ACTIVIDADES' de la planilla en Excel)."""
    linea = models.CharField(max_length=50, choices=Estudiante.LINEA_MEDIA, verbose_name='Línea')
    jornada = models.CharField(max_length=50, choices=Estudiante.JORNADA, verbose_name='Jornada')
    nombre = models.CharField(max_length=100, verbose_name='Nombre de la actividad')
    orden = models.PositiveIntegerField(default=0)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='actividades_creadas',
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'id']
        verbose_name = 'Actividad calificable'
        verbose_name_plural = 'Actividades calificables'

    def __str__(self):
        return f"{self.nombre} — {self.get_linea_display()} ({self.get_jornada_display()})"


class NotaActividad(models.Model):
    """Calificación (0.0 a 5.0) de un estudiante en una actividad."""
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='notas_actividades')
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='notas')
    valor = models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Nota (0.0 a 5.0)')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notas_registradas',
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['estudiante', 'actividad'], name='unica_nota_estudiante_actividad')
        ]
        verbose_name = 'Nota de actividad'
        verbose_name_plural = 'Notas de actividades'

    def __str__(self):
        return f"{self.estudiante} — {self.actividad.nombre}: {self.valor}"