import csv, io, zipfile, unicodedata
from datetime import datetime
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from .models import Estudiante, Asistencia
from .utils.pdf import generar_certificado_pdf
from .utils.carnet import generar_carnet_pdf
from .utils.carnet_png import generar_carnet_png
from .utils.mosaico_pdf import generar_mosaico_pdf_por_linea


# ══════════════════════════════════════════════════════════════════════════════
#  Filtros multi-selección para el Admin
# ══════════════════════════════════════════════════════════════════════════════

class MultiSelectFilter(admin.SimpleListFilter):
    """Base para filtros que aceptan múltiples valores vía ?param=A&param=B."""
    separator = ','

    def lookups(self, request, model_admin):
        raise NotImplementedError

    def _selected(self, request):
        val = request.GET.get(self.parameter_name, '')
        return [v for v in val.split(self.separator) if v]

    def queryset(self, request, queryset):
        vals = self._selected(request)
        if not vals:
            return queryset
        return queryset.filter(**{f'{self.field_path}__in': vals})

    def value(self):
        # Devuelve el primer valor (para compatibilidad con "selected" en el sidebar)
        vals = self.request.GET.get(self.parameter_name, '')
        return vals or None

    def choices(self, changelist):
        # Reconstruimos las URL para multi-selección tipo toggle
        self.request = changelist.params  # no disponible aquí
        yield {
            'selected': not changelist.get_query_string({self.parameter_name: ''}),
            'query_string': changelist.get_query_string(remove=[self.parameter_name]),
            'display': _('Todos'),
        }
        selected_vals = changelist.params.get(self.parameter_name, '').split(self.separator)
        selected_vals = [v for v in selected_vals if v]
        for lookup, title in self.lookup_choices:
            lookup = str(lookup)
            if lookup in selected_vals:
                new_vals = [v for v in selected_vals if v != lookup]
            else:
                new_vals = selected_vals + [lookup]
            qs = changelist.get_query_string({self.parameter_name: self.separator.join(new_vals)})
            yield {
                'selected': lookup in selected_vals,
                'query_string': qs,
                'display': title,
            }

    def queryset(self, request, queryset):
        val = request.GET.get(self.parameter_name, '')
        vals = [v for v in val.split(self.separator) if v]
        if not vals:
            return queryset
        return queryset.filter(**{f'{self.field_path}__in': vals})


class JornadaFilter(MultiSelectFilter):
    title        = 'Jornada'
    parameter_name = 'jornada'
    field_path   = 'jornada'

    def lookups(self, request, model_admin):
        self.lookup_choices = Estudiante.JORNADA
        return Estudiante.JORNADA


class GradoFilter(admin.SimpleListFilter):
    title          = 'Grado'
    parameter_name = 'grado'
    separator      = ','

    def lookups(self, request, model_admin):
        return [('10', '10°'), ('11', '11°')]

    def choices(self, changelist):
        yield {
            'selected': not changelist.params.get(self.parameter_name),
            'query_string': changelist.get_query_string(remove=[self.parameter_name]),
            'display': _('Todos'),
        }
        selected_vals = changelist.params.get(self.parameter_name, '').split(self.separator)
        selected_vals = [v for v in selected_vals if v]
        for lookup, title in self.lookup_choices:
            lookup = str(lookup)
            if lookup in selected_vals:
                new_vals = [v for v in selected_vals if v != lookup]
            else:
                new_vals = selected_vals + [lookup]
            qs = changelist.get_query_string({self.parameter_name: self.separator.join(new_vals)})
            yield {
                'selected': lookup in selected_vals,
                'query_string': qs,
                'display': title,
            }

    def queryset(self, request, queryset):
        val = request.GET.get(self.parameter_name, '')
        vals = [v for v in val.split(self.separator) if v]
        if not vals:
            return queryset
        from django.db.models import Q
        q = Q()
        for g in vals:
            q |= Q(curso__startswith=g)
        return queryset.filter(q)


class LineaFilter(MultiSelectFilter):
    title          = 'Línea de media'
    parameter_name = 'linea'
    field_path     = 'linea'

    def lookups(self, request, model_admin):
        self.lookup_choices = Estudiante.LINEA_MEDIA
        return Estudiante.LINEA_MEDIA


class LineaAsistenciaFilter(MultiSelectFilter):
    title          = 'Línea de media'
    parameter_name = 'linea'
    field_path     = 'estudiante__linea'

    def lookups(self, request, model_admin):
        self.lookup_choices = Estudiante.LINEA_MEDIA
        return Estudiante.LINEA_MEDIA


class JornadaAsistenciaFilter(MultiSelectFilter):
    title          = 'Jornada'
    parameter_name = 'jornada'
    field_path     = 'estudiante__jornada'

    def lookups(self, request, model_admin):
        self.lookup_choices = Estudiante.JORNADA
        return Estudiante.JORNADA


class GradoAsistenciaFilter(admin.SimpleListFilter):
    title          = 'Grado'
    parameter_name = 'grado'
    separator      = ','

    def lookups(self, request, model_admin):
        return [('10', '10°'), ('11', '11°')]

    def choices(self, changelist):
        yield {
            'selected': not changelist.params.get(self.parameter_name),
            'query_string': changelist.get_query_string(remove=[self.parameter_name]),
            'display': _('Todos'),
        }
        selected_vals = changelist.params.get(self.parameter_name, '').split(self.separator)
        selected_vals = [v for v in selected_vals if v]
        for lookup, title in self.lookup_choices:
            lookup = str(lookup)
            new_vals = [v for v in selected_vals if v != lookup] if lookup in selected_vals else selected_vals + [lookup]
            yield {
                'selected': lookup in selected_vals,
                'query_string': changelist.get_query_string({self.parameter_name: self.separator.join(new_vals)}),
                'display': title,
            }

    def queryset(self, request, queryset):
        val = request.GET.get(self.parameter_name, '')
        vals = [v for v in val.split(self.separator) if v]
        if not vals:
            return queryset
        from django.db.models import Q
        q = Q()
        for g in vals:
            q |= Q(estudiante__curso__startswith=g)
        return queryset.filter(q)


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers CSV
# ══════════════════════════════════════════════════════════════════════════════

def _csv_estudiantes(qs):
    campos = [
        ('documento','Documento'), ('tipo','Tipo Doc.'), ('apellidos','Apellidos'),
        ('nombres','Nombres'), ('jornada','Jornada'), ('curso','Curso'), ('linea','Linea'),
        ('celular','Celular'), ('email','Email'), ('acudiente','Acudiente'),
        ('parentesco','Parentesco'), ('tel_acudiente','Tel. Acudiente'),
        ('tel2_acudiente','Tel. Acudiente 2'), ('direccion','Direccion'),
        ('ocupacion_acudiente','Ocupacion Acudiente'), ('eps','EPS'),
        ('observaciones','Observaciones'),
    ]
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    r = HttpResponse(content_type='text/csv; charset=utf-8')
    r['Content-Disposition'] = f'attachment; filename=estudiantes_{ts}.csv'
    r.write('\ufeff')
    w = csv.writer(r)
    w.writerow([l for _, l in campos])
    for e in qs:
        w.writerow([getattr(e, f, '') or '' for f, _ in campos])
    return r


def _csv_asistencia(qs, tipos=None, nombre_archivo='asistencias'):
    """
    Exporta registros de Asistencia a CSV.
    tipos: lista de códigos a filtrar (ej. ['ALM','TAR']). None = todos.
    """
    ETIQUETAS = {
        'ALM': 'Almuerzo',
        'TAR': 'Llegada Tarde',
        'UNI': 'Porte de Uniforme',
        'ASI': 'Asistencia a Clase',
    }
    if tipos:
        qs = qs.filter(tipo__in=tipos)
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    r = HttpResponse(content_type='text/csv; charset=utf-8')
    r['Content-Disposition'] = f'attachment; filename={nombre_archivo}_{ts}.csv'
    r.write('\ufeff')
    w = csv.writer(r)
    w.writerow(['Fecha', 'Hora', 'Tipo', 'Descripcion',
                'Documento', 'Apellidos', 'Nombres',
                'Jornada', 'Curso', 'Linea'])
    for a in qs.select_related('estudiante').order_by('-fecha', '-hora'):
        e = a.estudiante
        w.writerow([
            a.fecha, a.hora,
            a.tipo, ETIQUETAS.get(a.tipo, a.tipo),
            e.documento, e.apellidos, e.nombres,
            e.jornada, e.curso, e.linea,
        ])
    return r


# ══════════════════════════════════════════════════════════════════════════════
#  Cuentas de acceso individuales (usuario y contraseña por estudiante)
# ══════════════════════════════════════════════════════════════════════════════

def _normalizar_texto(texto):
    """Quita tildes/ñ y deja solo caracteres ASCII."""
    texto = unicodedata.normalize('NFKD', texto or '')
    return texto.encode('ascii', 'ignore').decode('ascii')


def _username_desde_nombre(nombres, apellidos):
    """nombres+apellidos completos, en minúscula, sin tildes ni espacios. Ej: juancamilocortesperez"""
    base = _normalizar_texto(f"{nombres} {apellidos}").lower()
    base = ''.join(ch for ch in base if ch.isalnum())
    if not base:
        base = 'estudiante'
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        i += 1
        username = f"{base}{i}"
    return username


def _password_desde_documento(documento):
    """La contraseña es el número de documento (sin espacios)."""
    return ''.join((documento or '').split())


@admin.action(description='🔑 Crear acceso (usuario y contraseña)')
def crear_acceso_estudiantes(ma, request, qs):
    grupo, _creado = Group.objects.get_or_create(name='estudiante')
    creadas, omitidas = [], 0
    for e in qs:
        if e.usuario_id:
            omitidas += 1
            continue
        username = _username_desde_nombre(e.nombres, e.apellidos)
        password = _password_desde_documento(e.documento)
        user = User.objects.create_user(
            username=username, password=password,
            first_name=(e.nombres or '')[:30], last_name=(e.apellidos or '')[:30],
            email=e.email or '', is_staff=False,
        )
        user.groups.set([grupo])
        e.usuario = user
        e.debe_cambiar_clave = True
        e.save(update_fields=['usuario', 'debe_cambiar_clave'])
        creadas.append(f"{e.apellidos}, {e.nombres} → usuario: {username} / clave: {password}")
    if creadas:
        ma.message_user(
            request,
            "Cuentas creadas (usuario = nombre completo, clave = documento). "
            "Se les pedirá cambiar la contraseña al ingresar por primera vez: "
            + "  |  ".join(creadas),
            level='success',
        )
    if omitidas:
        ma.message_user(request, f"{omitidas} estudiante(s) ya tenían cuenta de acceso y se omitieron.", level='warning')


@admin.action(description='♻️ Restablecer contraseña (al número de documento)')
def restablecer_clave_estudiantes(ma, request, qs):
    resultados, sin_acceso = [], 0
    for e in qs:
        if not e.usuario_id:
            sin_acceso += 1
            continue
        password = _password_desde_documento(e.documento)
        e.usuario.set_password(password)
        e.usuario.save()
        e.debe_cambiar_clave = True
        e.save(update_fields=['debe_cambiar_clave'])
        resultados.append(f"{e.apellidos}, {e.nombres} → usuario: {e.usuario.username} / nueva clave: {password}")
    if resultados:
        ma.message_user(
            request,
            "Contraseñas restablecidas al número de documento (deberán cambiarla al ingresar): "
            + "  |  ".join(resultados),
            level='success',
        )
    if sin_acceso:
        ma.message_user(request, f"{sin_acceso} estudiante(s) no tienen cuenta de acceso creada.", level='warning')


@admin.action(description='🚫 Eliminar acceso al sistema')
def eliminar_acceso_estudiantes(ma, request, qs):
    total = 0
    for e in qs:
        if e.usuario_id:
            user = e.usuario
            e.usuario = None
            e.save(update_fields=['usuario'])
            user.delete()
            total += 1
    ma.message_user(request, f"Se eliminó el acceso al sistema de {total} estudiante(s).", level='success')


# ══════════════════════════════════════════════════════════════════════════════
#  Acciones — Estudiantes
# ══════════════════════════════════════════════════════════════════════════════

@admin.action(description='📥 Exportar selección a CSV')
def exportar_estudiantes_csv(ma, request, qs):
    return _csv_estudiantes(qs)


@admin.action(description='📄 Generar certificado (PDF)')
def generar_certificado(ma, request, qs):
    if not request.user.is_superuser:
        return
    if qs.count() != 1:
        ma.message_user(request, 'Seleccione un solo estudiante.', level='warning')
        return
    e = qs.first()
    pdf = generar_certificado_pdf(e)
    r = HttpResponse(pdf, content_type='application/pdf')
    r['Content-Disposition'] = f'attachment; filename=certificado_{e.documento}.pdf'
    return r


@admin.action(description='🪪 Generar carnet (PDF)')
def generar_carnet(ma, request, qs):
    if not request.user.is_superuser:
        return
    if qs.count() != 1:
        ma.message_user(request, 'Seleccione un solo estudiante.', level='warning')
        return
    e = qs.first()
    pdf = generar_carnet_pdf(e)
    r = HttpResponse(pdf, content_type='application/pdf')
    r['Content-Disposition'] = f'attachment; filename=carnet_{e.documento}.pdf'
    return r


@admin.action(description='🪪 Carnets seleccionados (ZIP de PDF)')
def generar_carnets_zip(ma, request, qs):
    if not request.user.is_superuser:
        return
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for e in qs:
            zf.writestr(f'carnet_{e.documento}.pdf', generar_carnet_pdf(e))
    buf.seek(0)
    r = HttpResponse(buf, content_type='application/zip')
    r['Content-Disposition'] = 'attachment; filename=carnets_pdf.zip'
    return r


@admin.action(description='🖼️ Carnets PNG automáticos (ZIP)')
def generar_carnets_png_zip(ma, request, qs):
    """
    Genera un carnet PNG por cada estudiante seleccionado.
    El fondo se elige AUTOMÁTICAMENTE según jornada + grado (10°/11°) + línea.
    Los archivos se organizan dentro del ZIP en carpetas por jornada/grado/línea.
    """
    if not request.user.is_superuser:
        return

    errores = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for e in qs:
            jornada_str = 'manana' if e.jornada == 'JM' else 'tarde'
            grado_str   = 'once'   if (e.curso or '').startswith('11') else 'decimo'
            linea_str   = (e.linea or 'OT').replace(' ', '_')
            carpeta_zip = f'{jornada_str}/{grado_str}/{linea_str}'
            try:
                img = generar_carnet_png(e)
                ib  = io.BytesIO()
                img.save(ib, format='PNG')
                zf.writestr(f'{carpeta_zip}/carnet_{e.documento}.png', ib.getvalue())
            except ValueError as exc:
                errores.append(str(exc))
            except Exception as exc:
                errores.append(f'{e.documento}: {exc}')

    if errores:
        for msg in errores[:5]:
            ma.message_user(request, msg, level='error')
        if len(errores) > 5:
            ma.message_user(request, f'...y {len(errores)-5} error(es) más.', level='error')
        if not buf.getvalue():
            return

    buf.seek(0)
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    r = HttpResponse(buf, content_type='application/zip')
    r['Content-Disposition'] = f'attachment; filename=carnets_png_{ts}.zip'
    return r


@admin.action(description='🗂️ Mosaico por línea (PDF)')
def generar_mosaico_linea(ma, request, qs):
    if not request.user.is_superuser:
        return
    linea = qs.first().linea
    pdf   = generar_mosaico_pdf_por_linea(qs.filter(linea=linea), linea)
    r = HttpResponse(pdf, content_type='application/pdf')
    r['Content-Disposition'] = f'attachment; filename=mosaico_{linea}.pdf'
    return r


# ══════════════════════════════════════════════════════════════════════════════
#  Acciones — Asistencia (exportar por tipo)
# ══════════════════════════════════════════════════════════════════════════════

@admin.action(description='📥 Exportar selección a CSV (todos los tipos)')
def exportar_asistencia_csv(ma, request, qs):
    return _csv_asistencia(qs, nombre_archivo='asistencias_todos')

@admin.action(description='🍽️ Exportar — Solo Almuerzos')
def exportar_almuerzos_csv(ma, request, qs):
    return _csv_asistencia(qs, tipos=['ALM'], nombre_archivo='almuerzos')

@admin.action(description='⏰ Exportar — Solo Llegadas Tarde')
def exportar_tardanzas_csv(ma, request, qs):
    return _csv_asistencia(qs, tipos=['TAR'], nombre_archivo='llegadas_tarde')

@admin.action(description='👔 Exportar — Solo Porte de Uniforme')
def exportar_uniforme_csv(ma, request, qs):
    return _csv_asistencia(qs, tipos=['UNI'], nombre_archivo='uniforme')

@admin.action(description='📋 Exportar — Solo Asistencia a Clase')
def exportar_asistencia_clase_csv(ma, request, qs):
    return _csv_asistencia(qs, tipos=['ASI'], nombre_archivo='asistencia_clase')


# ══════════════════════════════════════════════════════════════════════════════
#  Registro Admin
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display  = ['fecha', 'hora', 'tipo', 'get_nombres', 'get_apellidos',
                     'get_jornada', 'get_curso', 'get_linea']
    list_filter   = ['fecha', 'tipo', JornadaAsistenciaFilter,
                     GradoAsistenciaFilter, LineaAsistenciaFilter]
    search_fields = ['estudiante__nombres', 'estudiante__apellidos',
                     'estudiante__documento']
    ordering      = ['-fecha', '-hora']
    date_hierarchy = 'fecha'
    actions = [
        exportar_asistencia_csv,
        exportar_almuerzos_csv,
        exportar_tardanzas_csv,
        exportar_uniforme_csv,
        exportar_asistencia_clase_csv,
    ]

    def get_nombres(self, o):   return o.estudiante.nombres
    def get_apellidos(self, o): return o.estudiante.apellidos
    def get_jornada(self, o):   return o.estudiante.jornada
    def get_curso(self, o):     return o.estudiante.curso
    def get_linea(self, o):     return o.estudiante.linea

    get_nombres.short_description   = 'Nombres'
    get_apellidos.short_description = 'Apellidos'
    get_jornada.short_description   = 'Jornada'
    get_curso.short_description     = 'Curso'
    get_linea.short_description     = 'Línea'


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display  = ['documento', 'apellidos', 'nombres', 'jornada', 'curso', 'linea', 'tiene_acceso']
    search_fields = ['documento', 'nombres', 'apellidos', 'usuario__username']
    list_filter   = [JornadaFilter, GradoFilter, LineaFilter]
    readonly_fields = ['usuario']
    actions = [
        exportar_estudiantes_csv,
        generar_certificado,
        generar_carnet,
        generar_carnets_zip,
        generar_carnets_png_zip,
        generar_mosaico_linea,
        crear_acceso_estudiantes,
        restablecer_clave_estudiantes,
        eliminar_acceso_estudiantes,
    ]

    def tiene_acceso(self, obj):
        return bool(obj.usuario_id)
    tiene_acceso.short_description = 'Acceso al sistema'
    tiene_acceso.boolean = True

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            for n in ['generar_certificado', 'generar_carnet',
                      'generar_carnets_zip', 'generar_carnets_png_zip',
                      'generar_mosaico_linea', 'crear_acceso_estudiantes',
                      'restablecer_clave_estudiantes', 'eliminar_acceso_estudiantes']:
                actions.pop(n, None)
        return actions
