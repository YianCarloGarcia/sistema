from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from django.conf import settings
import os
import io

def generar_mosaico_pdf_por_linea(estudiantes, nombre_linea):
    buffer = io.BytesIO()

    c = canvas.Canvas(buffer, pagesize=landscape(A3))
    ancho, alto = landscape(A3)

    # ---------- FONDO ----------
    fondo_path = os.path.join(
        settings.BASE_DIR,
        'static',
        'mosaico',
        'fondo_a3.png'
    )

    # ---------- CONFIGURACIÓN GRILLA ----------
    columnas = 6
    filas = 4

    margen_x = 2 * cm
    margen_y = 2 * cm

    espacio_x = (ancho - 2 * margen_x) / columnas
    espacio_y = (alto - 2 * margen_y) / filas

    ancho_foto = espacio_x * 0.8
    alto_foto = espacio_y * 0.7

    x_offset = (espacio_x - ancho_foto) / 2
    y_offset = (espacio_y - alto_foto) / 2

    c.setFont("Helvetica-Bold", 10)

    for index, estudiante in enumerate(estudiantes):
        if index % (columnas * filas) == 0:
            if index > 0:
                c.showPage()

            # Fondo en cada página
            c.drawImage(
                fondo_path,
                0,
                0,
                width=ancho,
                height=alto,
                mask='auto'
            )

            # TÍTULO
            c.setFont("Helvetica-Bold", 24)
            c.drawCentredString(
                ancho / 2,
                alto - 1.2 * cm,
                f"MOSAICO – LÍNEA {nombre_linea.upper()}"
            )
            c.setFont("Helvetica-Bold", 10)

        pos = index % (columnas * filas)
        col = pos % columnas
        fila = pos // columnas

        x = margen_x + col * espacio_x + x_offset
        y = alto - margen_y - (fila + 1) * espacio_y + y_offset

        # ---------- FOTO ----------
        if estudiante.foto:
            foto_path = os.path.join(settings.MEDIA_ROOT, estudiante.foto.name)
            if os.path.exists(foto_path):
                c.drawImage(
                    foto_path,
                    x,
                    y + 1 * cm,
                    width=ancho_foto,
                    height=alto_foto,
                    preserveAspectRatio=True,
                    anchor='c',
                    mask='auto'
                )
                c.saveState()
                c.translate(x, y)
                c.rotate(90)
                c.drawImage(
                    foto_path,
                    0,
                    -alto_foto,
                    width=alto_foto,
                    height=ancho_foto,
                    mask='auto'
                )
                c.restoreState()

        # ---------- NOMBRE ----------
        nombre = f"{estudiante.nombres.upper()} {estudiante.apellidos.upper()}"
        c.drawCentredString(
            x + ancho_foto / 2,
            y,
            nombre
        )

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
