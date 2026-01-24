from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import qrcode
import io
import os
from django.conf import settings


FONDOS_CARNET = {
    'DIS': 'fondo_diseno.png',
    'ROB': 'fondo_robotica.png',  # por si viene sin tilde
    'BIO': 'fondo_biotecnologia.png',
    'COM': 'fondo_comunicacion.png',
    'TPS': 'fondo_programacion.png',
    'AA': 'fondo_asistencia.png',
    'ISERC': 'fondo_Electricidad.png',
    'otro': 'fondo_defalt.png',
}


def generar_carnet_pdf(estudiante):
    buffer = io.BytesIO()

    width = 5.4 * cm
    height = 8.6 * cm
    c = canvas.Canvas(buffer, pagesize=(width, height))

    # ---------- FONDO ----------
    linea = estudiante.linea.upper().strip()

    nombre_fondo = FONDOS_CARNET.get(linea, 'fondo_default.png')

    fondo_path = os.path.join(
        settings.BASE_DIR,
        'static',
        'carnet',
        nombre_fondo
    )

    c.drawImage( fondo_path, 0, 0,
        width=width,
        height=height,
        mask='auto'
    )
    # ---------- FOTO ROTADA 90° IZQUIERDA ----------
    if estudiante.foto:
        foto_path = os.path.join(settings.MEDIA_ROOT, estudiante.foto.name)
        if os.path.exists(foto_path):

            c.saveState()

            # Punto donde irá la foto
            x = 0.27 * cm
            y = 4.05 * cm

            # Rotar
            c.translate(x, y)
            c.rotate(90)

            c.drawImage(
                foto_path,
                0,
                -2.65 * cm,
                width=3.15 * cm,
                height=2.6 * cm,
                preserveAspectRatio=True,
                mask='auto'
            )

            c.restoreState()

    # ---------- TEXTO ----------
    c.setFillColorRGB(0, 0, 0)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        0.5 * cm,
        2.8 * cm,
        f"{estudiante.apellidos.upper()}"
    )

    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        0.5 * cm,
        3.3 * cm,
        f"{estudiante.nombres.upper()}"
    )

    c.setFont("Helvetica-Bold", 10)
    c.drawString(
        0.5 * cm,
        2.4 * cm,
        f"Doc: {estudiante.documento.upper()}"
    )

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
    )

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    qr_reader = ImageReader(qr_buffer)

    c.drawImage(
        qr_reader,
        0.5 * cm,
        0.5 * cm,
        width=1.8 * cm,
        height=1.8 * cm,
        mask='auto'
    )

    # ---------- FINAL ----------
    print("LÍNEA DEL ESTUDIANTE >>>", estudiante.linea)
    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer.getvalue()

