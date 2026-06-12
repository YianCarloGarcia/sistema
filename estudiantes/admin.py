from django.contrib import admin
from django.http import HttpResponse
from .models import Estudiante, Asistencia
from import_export import resources, fields
from import_export.admin import ExportMixin
import zipfile
import io

from .utils.pdf import generar_certificado_pdf
from .utils.carnet import generar_carnet_pdf
from .utils.carnet_png import generar_carnet_png
from .utils.mosaico_pdf import generar_mosaico_pdf_por_linea


# ============================================================
# Resources (solo para EXPORTACION — sin ImportExport)
# ============================================================

class EstudianteResource(resources.ModelResource):
    class Meta:
        model  = Estudiante
        fields = (
            'documento', 'tipo', 'apellidos', 'nombres',
            'jornada', 'curso', 'linea',
            'celular', 'email',
            'acudiente', 'parentesco', 'tel_acudiente', 'tel2_acudiente',
            'direccion', 'ocupacion_acudiente', 'eps', 'observaciones',
        )
        export_order = (
            'documento', 'tipo', 'apellidos', 'nombres',
            'jornada', 'curso', 'linea',
            'celular', 'email',
            'acudiente', 'parentesco', 'tel_acudiente', 'tel2_acudiente',
            'direccion', 'ocupacion_acudiente', 'eps', 'observaciones',
        )


class AsistenciaResource(resources.ModelResource):
    nombres  = fields.Field()
    apellidos = fields.Field()
    jornada  = fields.Field()
    curso    = fields.Field()
    linea    = fields.Field()

    class Meta:
        model  = Asistencia
        fields = ('fecha', 'hora', 'nombres', 'apellidos', 'jornada', 'curso', 'linea', 'tipo')
        export_order = ('fecha', 'hora', 'nombres', 'apellidos', 'jornada', 'curso', 'linea', 'tipo')

    def dehydrate_nombres(self, obj):   return obj.estudiante.nombres
    def dehydrate_apellidos(self, obj): return obj.estudiante.apellidos
    def dehydrate_jornada(self, obj):   return obj.estudiante.jornada
    def dehydrate_curso(self, obj):     return obj.estudiante.curso
    def dehydrate_linea(self, obj):     return obj.estudiante.linea


# ============================================================
# ACCIONES CARNETS / DOCUMENTOS
# ============================================================

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
generar_carnet.short_description = "🪪 Generar carnet (PDF)"


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
generar_certificado.short_description = "📄 Generar certificado (PDF)"


def generar_carnets_zip(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, "No tiene permisos", level='error')
        return
    buffer_zip = io.BytesIO()
    linea = None
    with zipfile.ZipFile(buffer_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for est in queryset:
            linea = est.linea
            pdf = generar_carnet_pdf(est)
            zf.writestr(f"carnet_{est.documento}.pdf", pdf)
    buffer_zip.seek(0)
    nombre = linea.replace(" ", "_") if linea else "carnets"
    response = HttpResponse(buffer_zip, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=carnets_{nombre}.zip'
    return response
generar_carnets_zip.short_description = "🪪 Generar carnets seleccionados (ZIP)"


def generar_carnets_png_zip(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, "Sin permisos", level='error')
        return
    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for est in queryset:
            img = generar_carnet_png(est)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            zf.writestr(f"carnet_{est.documento}.png", buf.getvalue())
    buffer_zip.seek(0)
    response = HttpResponse(buffer_zip, content_type="application/zip")
    response['Content-Disposition'] = 'attachment; filename=carnets_png.zip'
    return response
generar_carnets_png_zip.short_description = "🖼️ Carnets en PNG (ZIP)"


def generar_mosaico_linea(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, "Sin permisos", level='error')
        return
    linea = queryset.first().linea
    estudiantes = queryset.filter(linea=linea)
    pdf = generar_mosaico_pdf_por_linea(estudiantes, linea)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=mosaico_{linea}.pdf'
    return response
generar_mosaico_linea.short_description = "🗂️ Mosaico por línea (PDF)"


# ============================================================
# ADMIN ASISTENCIA — solo exportacion
# ============================================================

@admin.register(Asistencia)
class AsistenciaAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = AsistenciaResource

    list_display   = ('fecha', 'hora', 'tipo', 'get_nombres', 'get_apellidos',
                      'get_jornada', 'get_curso', 'get_linea')
    list_filter    = ('fecha', 'tipo', 'estudiante__jornada',
                      'estudiante__curso', 'estudiante__linea')
    search_fields  = ('estudiante__nombres', 'estudiante__apellidos',
                      'estudiante__documento')
    ordering       = ('-fecha', '-hora')
    date_hierarchy = 'fecha'

    def get_nombres(self, obj):   return obj.estudiante.nombres
    def get_apellidos(self, obj): return obj.estudiante.apellidos
    def get_jornada(self, obj):   return obj.estudiante.jornada
    def get_curso(self, obj):     return obj.estudiante.curso
    def get_linea(self, obj):     return obj.estudiante.linea

    get_nombres.short_description   = 'Nombres'
    get_apellidos.short_description = 'Apellidos'
    get_jornada.short_description   = 'Jornada'
    get_curso.short_description     = 'Curso'
    get_linea.short_description     = 'Línea'


# ============================================================
# ADMIN ESTUDIANTE — solo exportacion (sin Import/Excel)
# ============================================================

@admin.register(Estudiante)
class EstudianteAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = EstudianteResource

    list_display  = ('documento', 'apellidos', 'nombres', 'jornada', 'curso', 'linea')
    search_fields = ('documento', 'nombres', 'apellidos')
    list_filter   = ('jornada', 'curso', 'linea')

    actions = [
        generar_certificado,
        generar_carnet,
        generar_carnets_zip,
        generar_carnets_png_zip,
        generar_mosaico_linea,
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            for nombre in ['generar_certificado', 'generar_carnet',
                           'generar_carnets_zip', 'generar_carnets_png_zip',
                           'generar_mosaico_linea']:
                actions.pop(nombre, None)
        return actions
