from django.contrib import admin

# Register your models here. usuario: yianGarcia, correo: ycgarciabogota@gmail.com, password: mathic@s
# La base de datos se llama db.sqlite3 "estudiantes", el modelo se llama "Estudiante"

from .models import Estudiante, Asistencia
from import_export import resources
from import_export.admin import ExportMixin
from import_export.admin import ImportExportMixin
from django.http import HttpResponse
from .utils.pdf import generar_certificado_pdf
from import_export.admin import ImportExportModelAdmin


#admin.site.register(Estudiante)
#admin.site.register(Asistencia)
#@admin.register(Asistencia)
#@admin.register(Asistencia)

def generar_certificado(modeladmin, request, queryset):

    if not request.user.is_superuser:
        modeladmin.message_user(request, "No tiene permisos", level='error')
        return

    if queryset.count() != 1:
        modeladmin.message_user(request, "Seleccione un solo estudiante", level='warning')
        return

    estudiante = queryset.first()
    pdf = generar_certificado_pdf(estudiante)

    response = HttpResponse(pdf, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename=certificado_{estudiante.documento}.pdf'
    return response

generar_certificado.short_description = "📄 Generar certificado PDF"


class AsistenciaResource(resources.ModelResource):
    nombres = resources.Field()
    apellidos = resources.Field()
    jornada = resources.Field()
    curso = resources.Field()
    linea = resources.Field()

    class Meta:
        model = Asistencia
        fields = (
            'fecha',
            'hora',
            'nombres',
            'apellidos',
            'jornada',
            'curso',
            'linea',
        )
        export_order = fields

    # ====== CAMPOS CALCULADOS ======

    def dehydrate_nombres(self, obj):
        return obj.estudiante.nombres

    def dehydrate_apellidos(self, obj):
        return obj.estudiante.apellidos

    def dehydrate_jornada(self, obj):
        return obj.estudiante.jornada

    def dehydrate_curso(self, obj):
        return obj.estudiante.curso

    def dehydrate_linea(self, obj):
        return obj.estudiante.linea

@admin.register(Asistencia)
class AsistenciaAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = AsistenciaResource

    list_display = (
        'fecha',
        'hora',
        'get_nombres',
        'get_apellidos',
        'get_jornada',
        'get_curso',
        'get_linea',
    )

    list_filter = (
        'fecha',
        'estudiante__jornada',
        'estudiante__curso',
        'estudiante__linea',
    )

    search_fields = (
        'estudiante__nombres',
        'estudiante__apellidos',
        'estudiante__documento',
    )

    ordering = ('-fecha', '-hora')
    date_hierarchy = 'fecha'

    # ====== MÉTODOS ======

    def get_nombres(self, obj):
        return obj.estudiante.nombres
    get_nombres.short_description = 'Nombres'

    def get_apellidos(self, obj):
        return obj.estudiante.apellidos
    get_apellidos.short_description = 'Apellidos'

    def get_jornada(self, obj):
        return obj.estudiante.jornada
    get_jornada.short_description = 'Jornada'

    def get_curso(self, obj):
        return obj.estudiante.curso
    get_curso.short_description = 'Curso'

    def get_linea(self, obj):
        return obj.estudiante.linea
    get_linea.short_description = 'Línea'

class EstudianteResource(resources.ModelResource):
    class Meta:
        model = Estudiante
        import_id_fields = ('documento',)  # campo único
        skip_unchanged = True
        report_skipped = True

# ==========================
# ADMIN ESTUDIANTE
# ==========================
@admin.register(Estudiante)
class EstudianteAdmin(ImportExportModelAdmin):
    resource_class = EstudianteResource

    list_display = (
        'documento',
        'nombres',
        'apellidos',
        'jornada',
        'curso',
        'linea',
    )

    search_fields = (
        'documento',
        'nombres',
        'apellidos',
    )

    list_filter = (
        'jornada',
        'curso',
        'linea',
    )

    actions = [generar_certificado]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop('generar_certificado', None)
        return actions

