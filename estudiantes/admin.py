import csv, io, zipfile
from datetime import datetime
from django.contrib import admin
from django.http import HttpResponse
from .models import Estudiante, Asistencia
from .utils.pdf import generar_certificado_pdf
from .utils.carnet import generar_carnet_pdf
from .utils.carnet_png import generar_carnet_png
from .utils.mosaico_pdf import generar_mosaico_pdf_por_linea


def _csv_estudiantes(qs):
    campos = [('documento','Documento'),('tipo','Tipo Doc.'),('apellidos','Apellidos'),
              ('nombres','Nombres'),('jornada','Jornada'),('curso','Curso'),('linea','Linea'),
              ('celular','Celular'),('email','Email'),('acudiente','Acudiente'),
              ('parentesco','Parentesco'),('tel_acudiente','Tel. Acudiente'),
              ('tel2_acudiente','Tel. Acudiente 2'),('direccion','Direccion'),
              ('ocupacion_acudiente','Ocupacion Acudiente'),('eps','EPS'),('observaciones','Observaciones')]
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    r = HttpResponse(content_type='text/csv; charset=utf-8')
    r['Content-Disposition'] = f'attachment; filename=estudiantes_{ts}.csv'
    r.write('\ufeff')
    w = csv.writer(r)
    w.writerow([l for _,l in campos])
    for e in qs: w.writerow([getattr(e,f,''or'') for f,_ in campos])
    return r


def _csv_asistencia(qs):
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    r = HttpResponse(content_type='text/csv; charset=utf-8')
    r['Content-Disposition'] = f'attachment; filename=asistencias_{ts}.csv'
    r.write('\ufeff')
    w = csv.writer(r)
    w.writerow(['Fecha','Hora','Tipo','Documento','Apellidos','Nombres','Jornada','Curso','Linea'])
    for a in qs.select_related('estudiante'):
        e = a.estudiante
        w.writerow([a.fecha,a.hora,a.tipo,e.documento,e.apellidos,e.nombres,e.jornada,e.curso,e.linea])
    return r


@admin.action(description='📥 Exportar selección a CSV')
def exportar_estudiantes_csv(ma, request, qs): return _csv_estudiantes(qs)

@admin.action(description='📥 Exportar selección a CSV')
def exportar_asistencia_csv(ma, request, qs): return _csv_asistencia(qs)

@admin.action(description='📄 Generar certificado (PDF)')
def generar_certificado(ma, request, qs):
    if not request.user.is_superuser: return
    if qs.count()!=1: ma.message_user(request,"Seleccione un solo estudiante.",level='warning'); return
    e=qs.first(); pdf=generar_certificado_pdf(e)
    r=HttpResponse(pdf,content_type='application/pdf')
    r['Content-Disposition']=f'attachment; filename=certificado_{e.documento}.pdf'; return r

@admin.action(description='🪪 Generar carnet (PDF)')
def generar_carnet(ma, request, qs):
    if not request.user.is_superuser: return
    if qs.count()!=1: ma.message_user(request,"Seleccione un solo estudiante.",level='warning'); return
    e=qs.first(); pdf=generar_carnet_pdf(e)
    r=HttpResponse(pdf,content_type='application/pdf')
    r['Content-Disposition']=f'attachment; filename=carnet_{e.documento}.pdf'; return r

@admin.action(description='🪪 Carnets seleccionados (ZIP)')
def generar_carnets_zip(ma, request, qs):
    if not request.user.is_superuser: return
    buf=io.BytesIO(); linea=None
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as zf:
        for e in qs: linea=e.linea; zf.writestr(f'carnet_{e.documento}.pdf',generar_carnet_pdf(e))
    buf.seek(0); nombre=(linea or'carnets').replace(' ','_')
    r=HttpResponse(buf,content_type='application/zip')
    r['Content-Disposition']=f'attachment; filename=carnets_{nombre}.zip'; return r

@admin.action(description='🖼️ Carnets PNG (ZIP)')
def generar_carnets_png_zip(ma, request, qs):
    if not request.user.is_superuser: return
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as zf:
        for e in qs:
            img=generar_carnet_png(e); ib=io.BytesIO(); img.save(ib,format='PNG')
            zf.writestr(f'carnet_{e.documento}.png',ib.getvalue())
    buf.seek(0)
    r=HttpResponse(buf,content_type='application/zip')
    r['Content-Disposition']='attachment; filename=carnets_png.zip'; return r

@admin.action(description='🗂️ Mosaico por línea (PDF)')
def generar_mosaico_linea(ma, request, qs):
    if not request.user.is_superuser: return
    linea=qs.first().linea; pdf=generar_mosaico_pdf_por_linea(qs.filter(linea=linea),linea)
    r=HttpResponse(pdf,content_type='application/pdf')
    r['Content-Disposition']=f'attachment; filename=mosaico_{linea}.pdf'; return r


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display=['fecha','hora','tipo','get_nombres','get_apellidos','get_jornada','get_curso','get_linea']
    list_filter=['fecha','tipo','estudiante__jornada','estudiante__curso','estudiante__linea']
    search_fields=['estudiante__nombres','estudiante__apellidos','estudiante__documento']
    ordering=['-fecha','-hora']; date_hierarchy='fecha'; actions=[exportar_asistencia_csv]
    def get_nombres(self,o): return o.estudiante.nombres
    def get_apellidos(self,o): return o.estudiante.apellidos
    def get_jornada(self,o): return o.estudiante.jornada
    def get_curso(self,o): return o.estudiante.curso
    def get_linea(self,o): return o.estudiante.linea
    get_nombres.short_description='Nombres'; get_apellidos.short_description='Apellidos'
    get_jornada.short_description='Jornada'; get_curso.short_description='Curso'; get_linea.short_description='Línea'


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display=['documento','apellidos','nombres','jornada','curso','linea']
    search_fields=['documento','nombres','apellidos']; list_filter=['jornada','curso','linea']
    actions=[exportar_estudiantes_csv,generar_certificado,generar_carnet,generar_carnets_zip,generar_carnets_png_zip,generar_mosaico_linea]
    def get_actions(self,request):
        actions=super().get_actions(request)
        if not request.user.is_superuser:
            for n in ['generar_certificado','generar_carnet','generar_carnets_zip','generar_carnets_png_zip','generar_mosaico_linea']:
                actions.pop(n,None)
        return actions
