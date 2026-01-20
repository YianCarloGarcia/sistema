from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import qrcode
import io
import os
from django.conf import settings


def generar_carnet_pdf(estudiante):
    buffer = io.BytesIO()

    width = 8.6 * cm
    height = 5.4 * cm
    c = canvas.Canvas(buffer, pagesize=(width, height))

    # ---------- FONDO ----------
    fondo_path = os.path.join(settings.BASE_DIR, 'static', 'carnet', 'fondo_carnet.png')
    c.drawImage(fondo_path, 0, 0, width=width, height=height, mask='auto')

    # ---------- FOTO ROTADA 90° IZQUIERDA ----------
    if estudiante.foto:
        foto_path = os.path.join(settings.MEDIA_ROOT, estudiante.foto.name)
        if os.path.exists(foto_path):

            c.saveState()

            # Punto donde irá la foto
            x = 0.05 * cm
            y = 1.0 * cm

            # Rotar
            c.translate(x, y)
            c.rotate(90)

            c.drawImage(
                foto_path,
                0,
                -2.65 * cm,
                width=3.1 * cm,
                height=2.5 * cm,
                preserveAspectRatio=True,
                mask='auto'
            )

            c.restoreState()

    # ---------- TEXTO ----------
    c.setFillColorRGB(0, 0, 0)

    c.setFont("Arial-Bold", 8)
    c.drawCentredString(
        5.1 * cm,
        3.7 * cm,
        f"{estudiante.apellidos.upper()} {estudiante.nombres.upper()}"
    )

    c.setFont("Arial-Bold", 8)
    c.drawAlignedString(
        4.9 * cm,
        3.1 * cm,
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
        3.0 * cm,
        1.09 * cm,
        width=1.8 * cm,
        height=1.8 * cm,
        mask='auto'
    )

    # ---------- FINAL ----------
    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer.getvalue()
