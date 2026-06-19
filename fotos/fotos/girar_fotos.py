from PIL import Image, ImageOps
import os
from pathlib import Path

# Carpeta principal donde están las fotos
CARPETA_FOTOS = r"C:\Users\ycgar\Documentos\aplicacion\sistema\sistema\fotos\fotos"

# Crear carpeta de respaldo
BACKUP = os.path.join(CARPETA_FOTOS, "_backup_originales")
os.makedirs(BACKUP, exist_ok=True)

EXTENSIONES = ('.jpg', '.jpeg', '.png')


def corregir_foto(ruta):
    try:

        img = Image.open(ruta)

        # Corrige orientación EXIF
        img = ImageOps.exif_transpose(img)

        # Si sigue horizontal, la gira
        if img.width > img.height:
            img = img.rotate(90, expand=True)

        # Convertir a RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Respaldo
        nombre = os.path.basename(ruta)
        respaldo = os.path.join(BACKUP, nombre)

        if not os.path.exists(respaldo):
            import shutil
            shutil.copy2(ruta, respaldo)

        # Sobrescribir original
        img.save(ruta, quality=95)

        return True

    except Exception as e:
        print(f"ERROR: {ruta}")
        print(e)
        return False


procesadas = 0
errores = 0

for raiz, carpetas, archivos in os.walk(CARPETA_FOTOS):

    for archivo in archivos:

        if archivo.lower().endswith(EXTENSIONES):

            ruta = os.path.join(raiz, archivo)

            if corregir_foto(ruta):
                procesadas += 1
                print(f"OK -> {archivo}")
            else:
                errores += 1

print("\n========================")
print(f"Procesadas: {procesadas}")
print(f"Errores: {errores}")
print("========================")