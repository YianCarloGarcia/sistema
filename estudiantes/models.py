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
        ('CC',  'Cédula de Ciudadanía'),
        ('TI',  'Tarjeta de Identidad'),
        ('PPT', 'Permiso por Protección Temporal'),
        ('OT',  'Otro'),
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
    GRADOS = [
        ('10', '10°'),
        ('11', '11°'),
    ]
    jornada = models.CharField(max_length=50, choices=JORNADA, verbose_name="Jornada", default='JM')
    tipo = models.CharField(max_length=5,choices=TIPOS_DOCUMENTO, verbose_name="Tipo", default='CC')
    documento = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="Documento")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    curso = models.CharField(max_length=100, verbose_name="Curso")
    grado = models.CharField(
        max_length=5, choices=GRADOS, blank=True, db_index=True, verbose_name="Grado",
        help_text="Se usa para filtrar por 10°/11° sin depender del formato del código de curso.",
    )
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

    def save(self, *args, **kwargs):
        # Si no se indicó explícitamente el grado, se intenta deducir de los dos
        # primeros caracteres del curso (ej. "1101" -> "11"), pero SOLO si eso
        # coincide con un grado conocido (10/11). Si el curso viene en un formato
        # distinto (ej. "Décimo A"), el grado queda en blanco en vez de adivinar
        # mal — así el filtro por grado nunca clasifica algo de forma silenciosa
        # e incorrecta. Un grado puesto a mano nunca se sobreescribe aquí.
        if not self.grado and self.curso:
            prefijo = self.curso.strip()[:2]
            if prefijo in dict(self.GRADOS):
                self.grado = prefijo
        super().save(*args, **kwargs)

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
    puntos_aplicados = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
        verbose_name='Puntos aplicados',
        help_text=(
            'Puntos que tenía configurado este estado en el momento en que se registró. '
            'Queda fijo aquí a propósito: si luego se cambia la configuración de puntos '
            'del admin, las definitivas ya calculadas de meses anteriores NO cambian '
            'retroactivamente.'
        ),
    )
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
        estudiante_id/fecha/bloque/estado/puntos_aplicados) por bloque de clase y devuelve
        {estudiante_id: puntos}.

        Usa el puntaje que quedó guardado en cada registro en el momento en que se creó
        (`puntos_aplicados`), NO la configuración actual — así, cambiar la configuración de
        puntos hoy no altera retroactivamente las definitivas de meses anteriores.

        Varios ítems pueden coexistir en un mismo bloque y sus puntos se suman (ej: llegada
        tarde + uniforme incompleto). La única excepción: si en el mismo bloque coinciden
        Falla (F) y Excusa justificada (EX), la excusa remedia la falla y ese bloque no
        resta puntos en absoluto, sin importar los puntos que tuviera cada ítem guardado."""
        bloques = {}
        for r in registros:
            if isinstance(r, dict):
                clave = (r['estudiante_id'], r['fecha'], r['bloque'])
                estado = r['estado']
                puntos = r.get('puntos_aplicados', 0) or 0
            else:
                clave = (r.estudiante_id, r.fecha, r.bloque)
                estado = r.estado
                puntos = r.puntos_aplicados or 0
            bloques.setdefault(clave, []).append((estado, puntos))

        puntos_por_estudiante = {}
        for (estudiante_id, fecha, bloque), items in bloques.items():
            estados = {estado for estado, _ in items}
            if 'F' in estados and 'EX' in estados:
                puntos_bloque = 0
            else:
                puntos_bloque = sum(puntos for _, puntos in items)
            puntos_por_estudiante[estudiante_id] = puntos_por_estudiante.get(estudiante_id, 0) + puntos_bloque
        return puntos_por_estudiante

    @property
    def puntos(self):
        return self.puntos_aplicados


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


class Periodo(models.Model):
    """Periodo académico (tres por año). Las actividades de Notas pertenecen a un periodo, y la
    planilla de asistencia se asigna al periodo según su fecha. Nada se borra al cambiar de
    periodo: cada uno conserva su historial y el año completo se obtiene sumándolos."""
    anio = models.PositiveSmallIntegerField(verbose_name='Año')
    numero = models.PositiveSmallIntegerField(
        choices=[(1, 'Periodo 1'), (2, 'Periodo 2'), (3, 'Periodo 3')], verbose_name='Periodo',
    )
    fecha_inicio = models.DateField(verbose_name='Fecha de inicio')
    fecha_fin = models.DateField(verbose_name='Fecha de fin')

    # Fechas iniciales (editables en el admin): tres bloques de cuatro meses.
    FECHAS_POR_DEFECTO = {1: ((1, 1), (4, 30)), 2: ((5, 1), (8, 31)), 3: ((9, 1), (12, 31))}

    class Meta:
        ordering = ['anio', 'numero']
        constraints = [models.UniqueConstraint(fields=['anio', 'numero'], name='unico_periodo_anio_numero')]
        verbose_name = 'Periodo académico'
        verbose_name_plural = 'Periodos académicos'

    def __str__(self):
        return f"Periodo {self.numero} — {self.anio}"

    @property
    def nombre(self):
        return f"Periodo {self.numero}"

    @classmethod
    def asegurar_anio(cls, anio):
        """Crea los tres periodos del año con fechas por defecto si todavía no existen."""
        if cls.objects.filter(anio=anio).count() >= 3:
            return
        import datetime as _dt
        for numero, ((mi, di), (mf, df)) in cls.FECHAS_POR_DEFECTO.items():
            cls.objects.get_or_create(anio=anio, numero=numero, defaults={
                'fecha_inicio': _dt.date(anio, mi, di), 'fecha_fin': _dt.date(anio, mf, df),
            })

    @classmethod
    def actual(cls, hoy=None):
        """Periodo en curso: el que contiene la fecha; si cae en un hueco, el último iniciado."""
        hoy = hoy or timezone.localdate()
        cls.asegurar_anio(hoy.year)
        return (
            cls.objects.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).first()
            or cls.objects.filter(fecha_inicio__lte=hoy).order_by('-fecha_inicio').first()
            or cls.objects.order_by('fecha_inicio').first()
        )


class ConfiguracionPorcentajes(models.Model):
    """Peso de cada tipo de actividad en la nota del periodo. Una sola fila, editable desde el
    admin: el cambio se refleja de inmediato en Notas, exportes y en la vista del estudiante.
    Por defecto: actividades generales 70 %, evaluación trimestral 20 %, autoevaluación 10 %."""
    generales = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('70'),
                                    verbose_name='Actividades generales promediadas (%)')
    evaluacion = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('20'),
                                     verbose_name='Evaluación trimestral (%)')
    autoevaluacion = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10'),
                                         verbose_name='Autoevaluación (%)')

    class Meta:
        verbose_name = 'Porcentajes de la nota'
        verbose_name_plural = 'Porcentajes de la nota'

    def __str__(self):
        return f"Generales {self.generales}% · Evaluación {self.evaluacion}% · Autoevaluación {self.autoevaluacion}%"

    def clean(self):
        from django.core.exceptions import ValidationError
        valores = [self.generales, self.evaluacion, self.autoevaluacion]
        if any(v is None for v in valores):
            return
        if any(v < 0 for v in valores):
            raise ValidationError('Los porcentajes no pueden ser negativos.')
        if sum(valores) != Decimal('100'):
            raise ValidationError(f'Los porcentajes deben sumar 100 (ahora suman {sum(valores)}).')

    @classmethod
    def obtener(cls):
        obj = cls.objects.order_by('pk').first()
        return obj or cls.objects.create()

    def por_tipo(self):
        return {'GEN': self.generales, 'EVA': self.evaluacion, 'AUT': self.autoevaluacion}


class Actividad(models.Model):
    """Actividad calificable definida por el docente para su línea/jornada (equivalente a las
    columnas D:O 'ACTIVIDADES' de la planilla en Excel)."""
    linea = models.CharField(max_length=50, choices=Estudiante.LINEA_MEDIA, verbose_name='Línea')
    jornada = models.CharField(max_length=50, choices=Estudiante.JORNADA, verbose_name='Jornada')
    nombre = models.CharField(max_length=100, verbose_name='Nombre de la actividad')
    TIPOS = [
        ('GEN', 'Actividad general'),
        ('EVA', 'Evaluación trimestral'),
        ('AUT', 'Autoevaluación'),
    ]
    tipo = models.CharField(
        max_length=3, choices=TIPOS, default='GEN', verbose_name='Tipo',
        help_text='Define cuánto pesa en la nota (ver «Porcentajes de la nota» en el admin).',
    )
    periodo = models.ForeignKey(
        'Periodo', on_delete=models.PROTECT, null=True, blank=True, related_name='actividades',
        verbose_name='Periodo académico',
        help_text='Si se deja vacío se usa el periodo en curso. Un periodo con actividades no se puede borrar.',
    )
    orden = models.PositiveIntegerField(default=0)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='actividades_creadas',
    )
    creado = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.periodo_id is None:
            self.periodo = Periodo.actual()
        super().save(*args, **kwargs)

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
    observacion = models.CharField(max_length=300, blank=True, default='', verbose_name='Observación',
                                   help_text='Opcional: causa o comentario sobre esta calificación.')
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

# ── Actividad por línea (módulo de progreso gráfico) ────────────

NIVELES_DESEMPENO = [
    # (nota mínima, clave, etiqueta, color)
    (Decimal('4.6'), 'superior', 'Superior', '#16a34a'),
    (Decimal('4.0'), 'alto',     'Alto',     '#2563eb'),
    (Decimal('3.0'), 'basico',   'Básico',   '#d97706'),
    (Decimal('0'),   'bajo',     'Bajo',     '#dc2626'),
]


def nivel_desempeno(valor):
    """Devuelve (clave, etiqueta, color) del nivel de desempeño para una nota 0–5."""
    valor = Decimal(valor)
    for minimo, clave, etiqueta, color in NIVELES_DESEMPENO:
        if valor >= minimo:
            return clave, etiqueta, color
    return 'bajo', 'Bajo', '#dc2626'


class ActividadLinea(models.Model):
    """Actividad única de cada línea de media. Su nombre es el de la línea; el docente
    puede añadir una descripción que el estudiante verá junto a su gráfica."""
    linea = models.CharField(
        max_length=50, choices=[c for c in Estudiante.LINEA_MEDIA if c[0] != 'OT'],
        unique=True, verbose_name='Línea',
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción de la actividad')
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Actividad de línea'
        verbose_name_plural = 'Actividades de línea'

    @property
    def nombre(self):
        return self.get_linea_display()

    def __str__(self):
        return self.nombre


class CalificacionLinea(models.Model):
    """Nota (0.0 a 5.0) de un estudiante en la actividad de una línea."""
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='calificaciones_linea')
    linea = models.CharField(
        max_length=50, choices=[c for c in Estudiante.LINEA_MEDIA if c[0] != 'OT'], verbose_name='Línea',
    )
    valor = models.DecimalField(max_digits=3, decimal_places=2, verbose_name='Nota (0.0 a 5.0)')
    observacion = models.CharField(max_length=200, blank=True, verbose_name='Observación')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='calificaciones_linea_registradas',
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['estudiante', 'linea'], name='unica_calificacion_estudiante_linea'),
            models.CheckConstraint(condition=models.Q(valor__gte=0, valor__lte=5), name='calificacion_linea_0_a_5'),
        ]
        verbose_name = 'Calificación de línea'
        verbose_name_plural = 'Calificaciones de línea'

    def __str__(self):
        return f"{self.estudiante} — {self.get_linea_display()}: {self.valor}"
