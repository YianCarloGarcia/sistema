from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
from django.conf import settings

ANCHO = 540   # px
ALTO = 860    # px
PX_POR_CM = 100

FONDOS_CARNET = {
    'DIS': 'fondo_diseno.png',
    'ROB': 'fondo_robotica.png',
    'BIO': 'fondo_biotecnologia.png',
    'COM': 'fondo_comunicacion.png',
    'TPS': 'fondo_programacion.png',
    'AA': 'fondo_asistencia.png',
    'ISERC': 'fondo_Electricidad.png',
    'otro': 'fondo_defalt.png',
}

def generar_carnet_png(estudiante):

    # ---------- FONDO ----------
    linea = estudiante.linea.upper().strip()
    nombre_fondo = FONDOS_CARNET.get(linea, FONDOS_CARNET['otro'])

    fondo_path = os.path.join(
        settings.BASE_DIR,
        'static',
        'carnet',
        nombre_fondo
    )

    img = Image.open(fondo_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # ---------- FUENTES ----------
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arialbd.ttf')
    font_nombre = ImageFont.truetype(font_path, 30)
    font_doc = ImageFont.truetype(font_path, 30)

    # ---------- TEXTO (MISMAS POSICIONES DEL PDF) ----------
    # Apellidos → 0.5 cm, 2.8 cm
    draw.text(
        (0.5 * PX_POR_CM, ALTO - (2.4 * PX_POR_CM) - 30),
        estudiante.apellidos.upper(),
        fill="black",
        font=font_nombre
    )

    # Nombres → 0.5 cm, 3.3 cm
    draw.text(
        (0.5 * PX_POR_CM, ALTO - (2.9 * PX_POR_CM) - 30),
        estudiante.nombres.upper(),
        fill="black",
        font=font_nombre
    )

    # Documento → 0.5 cm, 2.4 cm
    draw.text(
        (0.5 * PX_POR_CM, ALTO - (2.0 * PX_POR_CM) - 30),
        f"Doc: {estudiante.documento}",
        fill="black",
        font=font_doc
    )

    # ---------- FOTO ROTADA 90° IZQUIERDA ----------
    if estudiante.foto:
        foto_path = os.path.join(settings.MEDIA_ROOT, estudiante.foto.name)
        if os.path.exists(foto_path):

            MARCO_ANCHO = 315 + 45 + 15
            MARCO_ALTO = 260 + 45 

            foto = Image.open(foto_path).resize((MARCO_ANCHO, MARCO_ALTO), Image.LANCZOS)
            foto = foto.rotate(90, expand=True)
# Escalar manteniendo proporción
            foto.thumbnail((MARCO_ANCHO, MARCO_ALTO), Image.LANCZOS)
            x = int(0.27 * PX_POR_CM + 20)
            y = int(ALTO - (4.05 * PX_POR_CM) - foto.height + 20)

            img.paste(foto, (x, y))

    # ---------- QR SIN FONDO ----------
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=0
    )
    qr.add_data(str(estudiante.documento))
    qr.make(fit=True)

    qr_img = qr.make_image(
        fill_color="black",
        back_color="transparent"
    ).resize((180, 180))

    qr_x = int(0.7 * PX_POR_CM - 15)
    qr_y = int(ALTO - (0.5 * PX_POR_CM) - 100)

    img.paste(qr_img, (qr_x, qr_y), qr_img)

    return img
