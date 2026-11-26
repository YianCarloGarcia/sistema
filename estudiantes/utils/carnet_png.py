from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import os
from django.conf import settings

ANCHO = 540
ALTO  = 860
PX_POR_CM = 100

FONDOS_LINEA = {
    'DIS':   'fondo_diseno',
    'ROB':   'fondo_robotica',
    'BIO':   'fondo_biotecnologia',
    'COM':   'fondo_comunicacion',
    'TPS':   'fondo_programacion',
    'AA':    'fondo_asistencia',
    'ISERC': 'fondo_electricidad',
}
FONDO_DEFAULT = 'fondo_default'

# Diferencias exactas entre JM y JT (tomadas de los archivos originales)
CONFIG_JORNADA = {
    'JM': {
        'texto_offset_y': -65,
        'doc_offset_y':   1,
        'foto_x_offset':   6,
        'foto_y_offset':  10,
    
        'qr_size':        145,
        'qr_x':           int(0.7 * PX_POR_CM - 50),
        'qr_y':           int(ALTO - (0.5 * PX_POR_CM) - 200),
    },
    'JT': {
        'texto_offset_y': -70,
        'doc_offset_y':    1,
        'foto_x_offset':   18,
        'foto_y_offset':   -22,
        'qr_size':        170,
        'qr_x':           int(0.7 * PX_POR_CM - 15),
        'qr_y':           int(ALTO - (0.5 * PX_POR_CM) - 200),
    },
}

BASE_CARNET = os.path.join(settings.BASE_DIR, 'static', 'carnet')


FUENTES_ALTERNATIVAS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
    '/Library/Fonts/Arial Bold.ttf',
]


def _cargar_fuente(tamano):
    """static/fonts/arialbd.ttf si existe; si no, una fuente del sistema; como último recurso la
    fuente escalable de Pillow (así el texto del carnet nunca sale diminuto)."""
    candidatas = [os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arialbd.ttf')] + FUENTES_ALTERNATIVAS
    for ruta in candidatas:
        try:
            return ImageFont.truetype(ruta, tamano)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:                      # Pillow antiguo, sin parámetro size
        return ImageFont.load_default()


def _buscar_archivo(carpeta, nombre_base):
    """Busca nombre_base.png o nombre_base.jpg en carpeta. Retorna ruta o None."""
    for ext in ('.png', '.jpg', '.jpeg'):
        ruta = os.path.join(carpeta, nombre_base + ext)
        if os.path.exists(ruta):
            return ruta
    return None


def _resolver_fondo(estudiante):
    """
    Busca el fondo en este orden de prioridad:
      1. static/carnet/<jornada>/<grado>/<fondo_linea>.*   ← específico
      2. static/carnet/<jornada>/<fondo_linea>.*           ← por jornada
      3. static/carnet/<fondo_linea>.*                     ← raíz
      4. static/carnet/<jornada>/<grado>/fondo_default.*   ← default específico
      5. static/carnet/<jornada>/fondo_default.*
      6. static/carnet/fondo_default.*                     ← último recurso
    Retorna la ruta completa o None si no existe nada.
    """
    jornada = (estudiante.jornada or '').upper().strip()
    curso   = (estudiante.curso   or '').strip()
    linea   = (estudiante.linea   or '').upper().strip()

    carpeta_jornada = 'manana' if jornada == 'JM' else 'tarde'
    carpeta_grado   = 'once'   if curso.startswith('11') else 'decimo'
    nombre_fondo    = FONDOS_LINEA.get(linea, FONDO_DEFAULT)

    carpetas_a_buscar = [
        os.path.join(BASE_CARNET, carpeta_jornada, carpeta_grado),
        os.path.join(BASE_CARNET, carpeta_jornada),
        BASE_CARNET,
    ]

    # Primero busca el fondo de la línea
    for carpeta in carpetas_a_buscar:
        ruta = _buscar_archivo(carpeta, nombre_fondo)
        if ruta:
            return ruta

    # Si no, busca el fondo por defecto
    for carpeta in carpetas_a_buscar:
        ruta = _buscar_archivo(carpeta, FONDO_DEFAULT)
        if ruta:
            return ruta

    return None


def generar_carnet_png(estudiante):
    """
    Genera y devuelve un objeto PIL.Image con el carnet del estudiante.
    Lanza ValueError si no se encuentra ningún fondo válido.
    """
    jornada = (estudiante.jornada or '').upper().strip()
    cfg     = CONFIG_JORNADA.get(jornada, CONFIG_JORNADA['JM'])

    # ── Fondo ────────────────────────────────────────────────────────────────
    fondo_path = _resolver_fondo(estudiante)
    if fondo_path is None:
        raise ValueError(
            f"No se encontró ningún fondo de carnet para el estudiante "
            f"{estudiante.documento} (jornada={estudiante.jornada}, "
            f"curso={estudiante.curso}, linea={estudiante.linea}). "
            f"Verifique que existan imágenes en static/carnet/"
        )

    img  = Image.open(fondo_path).convert('RGBA')
    img  = img.resize((ANCHO, ALTO), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    # ── Fuentes ──────────────────────────────────────────────────────────────
    font_nombre = font_doc = _cargar_fuente(35)

    # ── Texto ─────────────────────────────────────────────────────────────────
    oy  = cfg['texto_offset_y']
    oyd = cfg['doc_offset_y']

    draw.text(
        (0.5 * PX_POR_CM, ALTO - (2.7 * PX_POR_CM) + oy), 
        estudiante.apellidos.upper(),
        fill='black', font=font_nombre
    )
    draw.text(
        (0.5 * PX_POR_CM, ALTO - (3.0 * PX_POR_CM) + oy),
        estudiante.nombres.upper(),
        fill='black', font=font_nombre
    )
    draw.text(
        (0.5 * PX_POR_CM, ALTO - (3.1 * PX_POR_CM) + oyd),
        f'Doc: {estudiante.documento}',
        fill='black', font=font_doc
    )

    # ── Foto ─────────────────────────────────────────────────────────────────
    if estudiante.foto and estudiante.foto.name:
        try:
            # Se lee con el almacenamiento de Django (disco local o Cloudflare R2), no con una ruta
            # de archivo: en producción las fotos están en el bucket y no en el disco del servidor.
            with estudiante.foto.storage.open(estudiante.foto.name, 'rb') as archivo:
                foto = Image.open(io.BytesIO(archivo.read())).convert('RGBA')
            MARCO_ANCHO = 240
            MARCO_ALTO  = 290
            foto = foto.resize((MARCO_ANCHO, MARCO_ALTO), Image.LANCZOS)
            foto = foto.rotate(0, expand=True)
            foto.thumbnail((MARCO_ANCHO, MARCO_ALTO), Image.LANCZOS)
            x = int(0.27 * PX_POR_CM + cfg['foto_x_offset'])
            y = int(ALTO - (4.05 * PX_POR_CM) - foto.height + cfg['foto_y_offset'])
            img.paste(foto, (x, y))
        except Exception:
            pass  # Carnet se genera sin foto si hay problema de acceso

    # ── QR ───────────────────────────────────────────────────────────────────
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6, border=0
    )
    qr.add_data(str(estudiante.documento))
    qr.make(fit=True)
    qr_size = cfg['qr_size']
    qr_img  = qr.make_image(fill_color='black', back_color='transparent').resize((qr_size, qr_size))
    img.paste(qr_img, (cfg['qr_x'], cfg['qr_y']), qr_img)

    return img
