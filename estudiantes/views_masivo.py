"""
Creación masiva de cuentas (solo directivos):
  · Estudiantes: a todos los que aún no tienen acceso (con filtros opcionales). El navegador
    los procesa por lotes pequeños, para no superar el tiempo máximo de una petición.
  · Docentes: desde un archivo Excel o CSV (nombres, apellidos, correo, línea, jornada).
"""
import csv
import io
import secrets
import string

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .admin import _normalizar_texto, _password_desde_documento, _username_desde_nombre
from .models import DocentePerfil, Estudiante
from .views import solo_directivo

LOTE_ESTUDIANTES = 20
LINEAS_DOCENTE = {c: n for c, n in Estudiante.LINEA_MEDIA if c != 'OT'}
JORNADAS = dict(Estudiante.JORNADA)


def _sin_cuenta(request):
    """Estudiantes sin acceso, filtrados por los parámetros linea / jornada / grado."""
    p = request.POST if request.method == 'POST' else request.GET
    qs = Estudiante.objects.filter(usuario__isnull=True).exclude(documento='')
    if p.get('linea'):
        qs = qs.filter(linea=p['linea'])
    if p.get('jornada'):
        qs = qs.filter(jornada=p['jornada'])
    if p.get('grado') in ('10', '11'):
        qs = qs.filter(grado=p['grado'])
    return qs.order_by('id')


@login_required
@solo_directivo
def usuarios_masivo(request):
    return render(request, 'usuarios/masivo.html', {
        'lineas': Estudiante.LINEA_MEDIA,
        'jornadas': Estudiante.JORNADA,
        'pendientes': _sin_cuenta(request).count(),
        'lineas_docente': LINEAS_DOCENTE,
    })


@login_required
@solo_directivo
def contar_pendientes(request):
    return JsonResponse({'pendientes': _sin_cuenta(request).count()})


@login_required
@solo_directivo
@require_POST
def crear_estudiantes_lote(request):
    """Crea hasta LOTE_ESTUDIANTES cuentas y devuelve cuántas quedan por crear."""
    grupo, _ = Group.objects.get_or_create(name='estudiante')
    creados = errores = 0
    for e in list(_sin_cuenta(request)[:LOTE_ESTUDIANTES]):
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=_username_desde_nombre(e.nombres, e.apellidos),
                    password=_password_desde_documento(e.documento),
                    first_name=(e.nombres or '')[:30], last_name=(e.apellidos or '')[:30],
                    email=(e.email or '')[:254], is_staff=False,
                )
                user.groups.set([grupo])
                e.usuario = user
                e.debe_cambiar_clave = True
                e.save(update_fields=['usuario', 'debe_cambiar_clave'])
            creados += 1
        except Exception:
            errores += 1
    restantes = _sin_cuenta(request).count()
    # Si un lote solo produjo errores, se corta para que el navegador no repita sin fin.
    return JsonResponse({'creados': creados, 'errores': errores, 'restantes': restantes,
                         'detener': creados == 0 and errores > 0})


# ── Docentes desde archivo ──────────────────────────────────

COLUMNAS_DOCENTES = ['nombres', 'apellidos', 'correo', 'linea', 'jornada']


def _clave(txt):
    return ''.join(ch for ch in _normalizar_texto(str(txt or '')).lower() if ch.isalnum())


def _leer_filas(archivo):
    """Devuelve una lista de dicts con las columnas en minúscula, desde .xlsx o .csv."""
    nombre = archivo.name.lower()
    if nombre.endswith('.xlsx'):
        import openpyxl
        ws = openpyxl.load_workbook(archivo, read_only=True, data_only=True).active
        filas = [[('' if c is None else str(c).strip()) for c in r] for r in ws.iter_rows(values_only=True)]
    elif nombre.endswith('.csv'):
        crudo = archivo.read()
        try:
            texto = crudo.decode('utf-8-sig')
        except UnicodeDecodeError:
            texto = crudo.decode('latin-1')
        dialecto = ';' if texto.splitlines()[0].count(';') > texto.splitlines()[0].count(',') else ','
        filas = [[c.strip() for c in r] for r in csv.reader(io.StringIO(texto), delimiter=dialecto)]
    else:
        raise ValueError('El archivo debe ser .xlsx o .csv.')
    filas = [f for f in filas if any(f)]
    if not filas:
        raise ValueError('El archivo está vacío.')
    cab = [_clave(c) for c in filas[0]]
    alias = {'nombre': 'nombres', 'apellido': 'apellidos', 'email': 'correo', 'correoelectronico': 'correo',
             'lineaasignada': 'linea', 'usuario': 'usuario', 'username': 'usuario'}
    cab = [alias.get(c, c) for c in cab]
    faltan = [c for c in ('nombres', 'apellidos', 'linea', 'jornada') if c not in cab]
    if faltan:
        raise ValueError('Faltan columnas: ' + ', '.join(faltan) + '. Use la plantilla.')
    return [dict(zip(cab, f + [''] * (len(cab) - len(f)))) for f in filas[1:]]


def _normalizar_linea(valor):
    k = _clave(valor)
    for cod, nombre in LINEAS_DOCENTE.items():
        if k in (_clave(cod), _clave(nombre)):
            return cod
    return None


def _normalizar_jornada(valor):
    k = _clave(valor)
    mapa = {'jm': 'JM', 'manana': 'JM', 'jornadamanana': 'JM', 'jt': 'JT', 'tarde': 'JT', 'jornadatarde': 'JT'}
    return mapa.get(k)


def _clave_temporal():
    alfabeto = string.ascii_letters.replace('l', '').replace('I', '').replace('O', '') + '23456789'
    return ''.join(secrets.choice(alfabeto) for _ in range(10))


@login_required
@solo_directivo
@require_POST
def crear_docentes_archivo(request):
    archivo = request.FILES.get('archivo')
    if not archivo:
        messages.error(request, 'Seleccione un archivo.')
        return render(request, 'usuarios/masivo.html', _ctx_masivo(request))
    try:
        filas = _leer_filas(archivo)
    except ValueError as exc:
        messages.error(request, str(exc))
        return render(request, 'usuarios/masivo.html', _ctx_masivo(request))
    except Exception:
        messages.error(request, 'No se pudo leer el archivo. Compruebe que sea la plantilla en .xlsx o .csv.')
        return render(request, 'usuarios/masivo.html', _ctx_masivo(request))

    grupo, _ = Group.objects.get_or_create(name='docente')
    creados, rechazados = [], []
    for n, f in enumerate(filas, start=2):
        nombres, apellidos = f.get('nombres', '').strip(), f.get('apellidos', '').strip()
        linea, jornada = _normalizar_linea(f.get('linea')), _normalizar_jornada(f.get('jornada'))
        correo = f.get('correo', '').strip()
        usuario = _clave(f.get('usuario', ''))
        if not nombres or not apellidos:
            rechazados.append((n, f"{nombres} {apellidos}".strip() or '(vacía)', 'Faltan nombres o apellidos'))
            continue
        if not linea:
            rechazados.append((n, f"{nombres} {apellidos}", f"Línea no válida: «{f.get('linea', '')}»"))
            continue
        if not jornada:
            rechazados.append((n, f"{nombres} {apellidos}", f"Jornada no válida: «{f.get('jornada', '')}» (use JM/JT, Mañana o Tarde)"))
            continue
        if usuario and User.objects.filter(username=usuario).exists():
            rechazados.append((n, f"{nombres} {apellidos}", f"El usuario «{usuario}» ya existe"))
            continue
        if correo and '@' not in correo:
            rechazados.append((n, f"{nombres} {apellidos}", f"Correo no válido: «{correo}»"))
            continue
        clave = _clave_temporal()
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=usuario or _username_desde_nombre(nombres, apellidos),
                    password=clave, first_name=nombres[:30], last_name=apellidos[:30],
                    email=correo[:254], is_staff=False,
                )
                user.groups.set([grupo])
                DocentePerfil.objects.create(usuario=user, linea=linea, jornada=jornada)
        except Exception as exc:
            rechazados.append((n, f"{nombres} {apellidos}", f"No se pudo crear: {exc}"))
            continue
        creados.append({'usuario': user.username, 'clave': clave, 'nombre': f"{nombres} {apellidos}",
                        'linea': LINEAS_DOCENTE[linea], 'jornada': JORNADAS[jornada]})
    return render(request, 'usuarios/masivo_resultado.html', {'creados': creados, 'rechazados': rechazados})


def _ctx_masivo(request):
    return {'lineas': Estudiante.LINEA_MEDIA, 'jornadas': Estudiante.JORNADA,
            'pendientes': _sin_cuenta(request).count(), 'lineas_docente': LINEAS_DOCENTE}


@login_required
@solo_directivo
def plantilla_docentes(request):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Docentes'
    ws.append(COLUMNAS_DOCENTES)
    ws.append(['Ana María', 'Pérez Gómez', 'ana.perez@colegio.edu.co', 'ROB', 'JM'])
    ws.append(['Carlos', 'Rojas Díaz', '', 'Biotecnología', 'Tarde'])
    for col, ancho in zip('ABCDE', (22, 24, 32, 18, 12)):
        ws.column_dimensions[col].width = ancho
    ws2 = wb.create_sheet('Valores válidos')
    ws2.append(['Línea (código)', 'Línea (nombre)'])
    for cod, nombre in LINEAS_DOCENTE.items():
        ws2.append([cod, nombre])
    ws2.append([])
    ws2.append(['Jornada: JM = Mañana, JT = Tarde'])
    buf = io.BytesIO()
    wb.save(buf)
    r = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    r['Content-Disposition'] = 'attachment; filename="plantilla_docentes.xlsx"'
    return r
