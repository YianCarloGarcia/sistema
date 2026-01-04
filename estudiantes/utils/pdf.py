from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from io import BytesIO
from django.contrib.staticfiles import finders


def generar_certificado_pdf(estudiante):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    elementos = []

    # 🔹 Encabezado (ruta segura)
    encabezado = finders.find("certificados/encabezado.png")
    if encabezado:
        elementos.append(Image(encabezado, width=18*cm, height=3*cm))
        elementos.append(Spacer(1, 1.5*cm))

    # 🔹 Texto
    texto = f"""
    La institución educativa certifica que el estudiante
    <b>{estudiante.nombres} {estudiante.apellidos}</b>,
    identificado con documento número <b>{estudiante.documento}</b>,
    se encuentra matriculado en el curso <b>{estudiante.curso}</b>,
    jornada <b>{estudiante.jornada}</b>,
    en la línea de profundización <b>{estudiante.linea}</b>.
    """
    elementos.append(Paragraph(texto, styles["Normal"]))
    elementos.append(Spacer(1, 2*cm))

    # 🔹 Firma (ruta segura)
    firma = finders.find("certificados/firma.png")
    if firma:
        elementos.append(Image(firma, width=6*cm, height=2*cm))

    doc.build(elementos)
    buffer.seek(0)
    return buffer
