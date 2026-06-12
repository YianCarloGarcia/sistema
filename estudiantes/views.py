from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Estudiante, Asistencia
from .forms import EstudianteForm
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CAMPOS_EXPORTAR = [
    ('documento',           'Documento'),
    ('tipo',                'Tipo Doc.'),
    ('apellidos',           'Apellidos'),
    ('nombres',             'Nombres'),
    ('jornada',             'Jornada'),
    ('curso',               'Curso'),
    ('linea',               'Linea'),
    ('celular',             'Celular'),
    ('email',               'Email'),
    ('acudiente',           'Acudiente'),
    ('parentesco',          'Parentesco'),
    ('tel_acudiente',       'Tel. Acudiente'),
    ('tel2_acudiente',      'Tel. Acudiente 2'),
    ('direccion',           'Direccion'),
    ('ocupacion_acudiente', 'Ocupacion Acudiente'),
    ('eps',                 'EPS'),
    ('observaciones',       'Observaciones'),
]

CAMPOS_IMPORTAR_REQUERIDOS = ['documento', 'apellidos', 'nombres', 'jornada', 'curso', 'linea']
VALORES_JORNADA = [v for v, _ in Estudiante.JORNADA]
VALORES_LINEA   = [v for v, _ in Estudiante.LINEA_MEDIA]
VALORES_TIPO    = [v for v, _ in Estudiante.TIPOS_DOCUMENTO]


def _qs_filtrada(request_get):
    qs = Estudiante.objects.all().order_by('apellidos', 'nombres')
    q       = request_get.get('q', '').strip()
    jornada = request_get.get('jornada', '')
    curso   = request_get.get('curso', '')
    linea   = request_get.get('linea', '')
    if q:
        qs = qs.filter(Q(nombres__icontains=q) | Q(apellidos__icontains=q) | Q(documento__icontains=q))
    if jornada:
        qs = qs.filter(jornada=jornada)
    if curso:
        qs = qs.filter(curso__iexact=curso)
    if linea:
        qs = qs.filter(linea=linea)
    return qs


def _build_excel(queryset):
    """Genera un archivo Excel con los datos del queryset."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Estudiantes"

    # Estilos encabezado
    header_fill = PatternFill("solid", fgColor="1a3a6e")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Side(style="thin", color="D1D5DB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = [label for _, label in CAMPOS_EXPORTAR]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill   = header_fill
        cell.font   = header_font
        cell.alignment = header_align
        cell.border = border

    ws.row_dimensions[1].height = 28

    # Datos
    alt_fill = PatternFill("solid", fgColor="F8FAFC")
    for row_idx, est in enumerate(queryset, 2):
        for col_idx, (field, _) in enumerate(CAMPOS_EXPORTAR, 1):
            val = getattr(est, field, '') or ''
            cell = ws.cell(row=row_idx, column=col_idx, value=str(val))
            cell.alignment = Alignment(vertical="center")
            cell.border = border
            if row_idx % 2 == 0:
                cell.fill = alt_fill

    # Anchos de columna
    anchos = [14, 8, 20, 20, 10, 8, 10, 14, 24, 22, 12, 14, 14, 24, 20, 14, 30]
    for i, ancho in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _leer_excel(archivo):
    """Lee el Excel subido y retorna (filas_dict, errores_globales)."""
    try:
        wb = openpyxl.load_workbook(archivo, data_only=True)
    except Exception as e:
        return None, [f"No se pudo leer el archivo: {e}"]

    ws = wb.active
    headers_raw = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    headers = [str(h).strip() if h else '' for h in headers_raw]

    # Mapeo label → field
    label_to_field = {label: field for field, label in CAMPOS_EXPORTAR}
    col_map = {}  # col_index (0-based) → field_name
    for i, h in enumerate(headers):
        if h in label_to_field:
            col_map[i] = label_to_field[h]

    if 'documento' not in col_map.values():
        return None, ["El archivo no tiene una columna 'Documento'. Descargue la plantilla y úsela como base."]

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        fila = {}
        for i, field in col_map.items():
            val = row[i] if i < len(row) else None
            fila[field] = str(val).strip() if val is not None else ''
        filas.append(fila)

    return filas, []


# ---------------------------------------------------------------------------
# Vistas principales
# ---------------------------------------------------------------------------

@login_required
def inicio(request):
    return render(request, 'paginas/inicio.html')

@login_required
def nosotros(request):
    return render(request, 'paginas/nosotros.html')

@login_required
def estudiantes(request):
    qs = _qs_filtrada(request.GET)
    total_filtrado = qs.count()

    paginator = Paginator(qs, 25)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    cursos_disponibles = (
        Estudiante.objects.values_list('curso', flat=True).distinct().order_by('curso')
    )

    return render(request, 'estudiantes/index.html', {
        'page_obj':           page_obj,
        'total_filtrado':     total_filtrado,
        'total_general':      Estudiante.objects.count(),
        'cursos_disponibles': cursos_disponibles,
        'jornadas':           Estudiante.JORNADA,
        'lineas':             Estudiante.LINEA_MEDIA,
        'filtro_q':       request.GET.get('q', ''),
        'filtro_jornada': request.GET.get('jornada', ''),
        'filtro_curso':   request.GET.get('curso', ''),
        'filtro_linea':   request.GET.get('linea', ''),
    })

@login_required
def crear(request):
    formulario = EstudianteForm(request.POST or None, request.FILES or None)
    if formulario.is_valid():
        formulario.save()
        return redirect('estudiantes')
    return render(request, 'estudiantes/crear.html', {'formulario': formulario})

@login_required
def editar(request, id):
    estudiante = Estudiante.objects.get(id=id)
    formulario = EstudianteForm(request.POST or None, request.FILES or None, instance=estudiante)
    if formulario.is_valid() and request.POST:
        formulario.save()
        return redirect('estudiantes')
    return render(request, 'estudiantes/editar.html', {'formulario': formulario})

@login_required
def eliminar(request, id):
    estudiante = Estudiante.objects.get(id=id)
    estudiante.delete()
    return redirect('estudiantes')

@login_required
def detalle(request, id):
    estudiante = Estudiante.objects.get(id=id)
    return render(request, 'estudiantes/detalle.html', {'estudiante': estudiante})


BLOQUEO_SEGUNDOS = 5

@login_required
def almuerzo(request):
    mensaje = contador = nombre = None
    if request.method == 'POST':
        documento = request.POST.get('documento', '').strip()
        try:
            estudiante = Estudiante.objects.get(documento=documento)
            ahora  = timezone.now()
            limite = ahora - timedelta(seconds=BLOQUEO_SEGUNDOS)
            ultimo = Asistencia.objects.filter(
                estudiante=estudiante, tipo='ALM'
            ).order_by('-fecha', '-hora').first()

            if ultimo:
                fhu = timezone.make_aware(timezone.datetime.combine(ultimo.fecha, ultimo.hora))
                if fhu > limite:
                    mensaje = f"Espere {BLOQUEO_SEGUNDOS} segundos antes de volver a escanear"
                else:
                    Asistencia.objects.create(estudiante=estudiante, tipo='ALM')
            else:
                Asistencia.objects.create(estudiante=estudiante, tipo='ALM')

            hoy      = timezone.localdate()
            contador = Asistencia.objects.filter(estudiante=estudiante, fecha=hoy, tipo='ALM').count()
            nombre   = f"{estudiante.nombres} {estudiante.apellidos}"
            mensaje  = f"Almuerzos registrados hoy: {contador}"
        except Estudiante.DoesNotExist:
            mensaje = "Documento no encontrado"

    return render(request, 'estudiantes/almuerzo.html',
                  {'mensaje': mensaje, 'contador': contador, 'nombre': nombre})

def exit(request):
    logout(request)
    return redirect('inicio')


# ---------------------------------------------------------------------------
# Gestión masiva
# ---------------------------------------------------------------------------

@login_required
def gestion_masiva(request):
    cursos_disponibles = (
        Estudiante.objects.values_list('curso', flat=True).distinct().order_by('curso')
    )
    return render(request, 'estudiantes/gestion_masiva.html', {
        'total': Estudiante.objects.count(),
        'campos': CAMPOS_EXPORTAR,
        'jornadas': Estudiante.JORNADA,
        'lineas':   Estudiante.LINEA_MEDIA,
        'cursos_disponibles': cursos_disponibles,
    })


@login_required
def exportar_estudiantes(request):
    qs = _qs_filtrada(request.GET)
    buf = _build_excel(qs)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=estudiantes.xlsx'
    return response


@login_required
def importar_estudiantes(request):
    """
    GET  → muestra formulario de carga
    POST con archivo → previsualización (sin guardar)
    POST con confirm=1 → guarda en base de datos
    """
    if request.method == 'POST':

        # ---- PASO 2: confirmar y guardar ----
        if request.POST.get('confirm') == '1':
            import json
            filas_json = request.POST.get('filas_json', '[]')
            try:
                filas = json.loads(filas_json)
            except Exception:
                messages.error(request, "Error al procesar los datos. Intente de nuevo.")
                return redirect('gestion_masiva')

            creados = actualizados = omitidos = 0
            for fila in filas:
                if fila.get('_error'):
                    omitidos += 1
                    continue
                doc = fila.get('documento', '').strip()
                if not doc:
                    omitidos += 1
                    continue
                campos = {k: v for k, v in fila.items() if not k.startswith('_') and k != 'documento'}
                obj, creado = Estudiante.objects.update_or_create(
                    documento=doc,
                    defaults=campos,
                )
                if creado:
                    creados += 1
                else:
                    actualizados += 1

            messages.success(
                request,
                f"Importación completa: {creados} creados, {actualizados} actualizados, {omitidos} omitidos por errores."
            )
            return redirect('gestion_masiva')

        # ---- PASO 1: previsualizar ----
        archivo = request.FILES.get('archivo')
        if not archivo:
            messages.error(request, "Seleccione un archivo Excel.")
            return redirect('gestion_masiva')

        filas, errores_globales = _leer_excel(archivo)
        if errores_globales:
            for e in errores_globales:
                messages.error(request, e)
            return redirect('gestion_masiva')

        # Validar cada fila
        preview = []
        for i, fila in enumerate(filas, 1):
            row = dict(fila)
            errores = []

            # Campos requeridos
            for campo in CAMPOS_IMPORTAR_REQUERIDOS:
                if not row.get(campo, '').strip():
                    errores.append(f"'{campo}' es requerido")

            # Valores de choice
            if row.get('jornada') and row['jornada'] not in VALORES_JORNADA:
                errores.append(f"Jornada '{row['jornada']}' inválida (use: {', '.join(VALORES_JORNADA)})")
            if row.get('linea') and row['linea'] not in VALORES_LINEA:
                errores.append(f"Línea '{row['linea']}' inválida (use: {', '.join(VALORES_LINEA)})")
            if row.get('tipo') and row['tipo'] not in VALORES_TIPO:
                errores.append(f"Tipo '{row['tipo']}' inválido (use: {', '.join(VALORES_TIPO)})")

            # Estado en BD
            doc = row.get('documento', '').strip()
            existe = Estudiante.objects.filter(documento=doc).exists() if doc else False

            row['_fila']   = i
            row['_errores'] = errores
            row['_error']   = bool(errores)
            row['_existe']  = existe  # True = actualización, False = nuevo
            preview.append(row)

        validos   = [r for r in preview if not r['_error']]
        invalidos = [r for r in preview if r['_error']]

        import json
        return render(request, 'estudiantes/importar_preview.html', {
            'preview':    preview,
            'validos':    len(validos),
            'invalidos':  len(invalidos),
            'filas_json': json.dumps(preview),
        })

    return redirect('gestion_masiva')


@login_required
def editar_masivo(request):
    """
    Aplica cambios de campo en lote sobre un grupo filtrado.
    """
    if request.method != 'POST':
        return redirect('gestion_masiva')

    # Filtros que definen el grupo
    jornada = request.POST.get('filtro_jornada', '')
    curso   = request.POST.get('filtro_curso', '')
    linea   = request.POST.get('filtro_linea', '')

    if not (jornada or curso or linea):
        messages.error(request, "Defina al menos un filtro para identificar el grupo a editar.")
        return redirect('gestion_masiva')

    qs = Estudiante.objects.all()
    if jornada: qs = qs.filter(jornada=jornada)
    if curso:   qs = qs.filter(curso__iexact=curso)
    if linea:   qs = qs.filter(linea=linea)

    if not qs.exists():
        messages.warning(request, "No se encontraron estudiantes con esos filtros.")
        return redirect('gestion_masiva')

    # Campos a cambiar (solo los que vienen con valor)
    cambios = {}
    nuevo_jornada = request.POST.get('nuevo_jornada', '').strip()
    nuevo_curso   = request.POST.get('nuevo_curso', '').strip()
    nuevo_linea   = request.POST.get('nuevo_linea', '').strip()

    if nuevo_jornada and nuevo_jornada in VALORES_JORNADA:
        cambios['jornada'] = nuevo_jornada
    if nuevo_curso:
        cambios['curso'] = nuevo_curso
    if nuevo_linea and nuevo_linea in VALORES_LINEA:
        cambios['linea'] = nuevo_linea

    if not cambios:
        messages.warning(request, "No se indicaron campos a cambiar.")
        return redirect('gestion_masiva')

    total = qs.count()
    qs.update(**cambios)

    campos_str = ', '.join(f"{k} → {v}" for k, v in cambios.items())
    messages.success(request, f"Se actualizaron {total} estudiantes: {campos_str}.")
    return redirect('gestion_masiva')
