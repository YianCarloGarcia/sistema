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
from .utils.carnet import generar_carnet_pdf
from django.http import HttpResponse
import zipfile
import io
<<<<<<< HEAD
from .utils.carnet_png import generar_carnet_png
=======
>>>>>>> e0bb138841ee3d150a652466f3f839d4b0c42f65

#admin.site.register(Estudiante)
#admin.site.register(Asistencia)
#@admin.register(Asistencia)
#@admin.register(Asistencia)

def generar_carnet(modeladmin, request, queryset):

    if not request.user.is_superuser:
        modeladmin.message_user(request, "Sin permisos", level='error')
        return

    if queryset.count() != 1:
        modeladmin.message_user(request, "Seleccione un solo estudiante", level='warning')
        return

    estudiante = queryset.first()
    pdf = generar_carnet_pdf(estudiante)

    response = HttpResponse(pdf, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename=carnet_{estudiante.documento}.pdf'
    return response

generar_carnet.short_description = "🪪 Generar carnet"


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

def generar_carnets_por_linea(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, "No tiene permisos", level='error')
        return

    buffer_zip = io.BytesIO()
    linea = None

    with zipfile.ZipFile(buffer_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for estudiante in queryset:
            linea = estudiante.linea
            pdf = generar_carnet_pdf(estudiante)
            nombre_archivo = f"carnet_{estudiante.documento}.pdf"
            zip_file.writestr(nombre_archivo, pdf)

    buffer_zip.seek(0)

    nombre_linea = linea.replace(" ", "_") if linea else "linea"

    response = HttpResponse(
        buffer_zip,
        content_type='application/zip'
    )
    response['Content-Disposition'] = (
        f'attachment; filename=carnets_{nombre_linea}.zip'
    )
    return response

generar_carnets_por_linea.short_description = "🪪 Generar carnets por línea (ZIP)"


def generar_carnets_png_zip(modeladmin, request, queryset):

    if not request.user.is_superuser:
        modeladmin.message_user(request, "Sin permisos", level='error')
        return

    buffer_zip = io.BytesIO()

    with zipfile.ZipFile(buffer_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for estudiante in queryset:
            img = generar_carnet_png(estudiante)

            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)

            nombre = f"carnet_{estudiante.documento}.png"
            zip_file.writestr(nombre, img_buffer.getvalue())

    buffer_zip.seek(0)

    response = HttpResponse(buffer_zip, content_type="application/zip")
    response['Content-Disposition'] = 'attachment; filename=carnets_png.zip'
    return response

generar_carnets_png_zip.short_description = "🖼️ Carnets en PNG (ZIP)"
=======
>>>>>>> e0bb138841ee3d150a652466f3f839d4b0c42f65

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

<<<<<<< HEAD
    actions = [generar_certificado, generar_carnet, generar_carnets_por_linea, generar_carnets_png_zip,
=======
    actions = [generar_certificado, generar_carnet, generar_carnets_por_linea,
>>>>>>> e0bb138841ee3d150a652466f3f839d4b0c42f65
]
    

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop('generar_certificado', None)
            actions.pop('generar_carnet', None)
            actions.pop('generar_carnets_por_linea', None)
        return actions

