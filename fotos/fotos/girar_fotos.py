from PIL import Image, ImageOps
import os
import shutil

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA_FOTOS = r"C:\Users\ycgar\Documentos\aplicacion\sistema\sistema\fotos\fotos"

CREAR_BACKUP = True

# ==========================================
# PROCESAMIENTO
# ==========================================

if CREAR_BACKUP:
    BACKUP_DIR = os.path.join(CARPETA_FOTOS, "_BACKUP_ORIGINALES")
    os.makedirs(BACKUP_DIR, exist_ok=True)

procesadas = 0
errores = 0
rotadas = 0
transparencias = 0

for raiz, _, archivos in os.walk(CARPETA_FOTOS):

    # Evitar procesar la carpeta de respaldo
    if "_BACKUP_ORIGINALES" in raiz:
        continue

    for archivo in archivos:

        if not archivo.lower().endswith(
            (".jpg", ".jpeg", ".png", ".bmp", ".webp")
        ):
            continue

        ruta = os.path.join(raiz, archivo)

        try:

            if CREAR_BACKUP:

                respaldo = os.path.join(
                    BACKUP_DIR,
                    os.path.relpath(ruta, CARPETA_FOTOS)
                )

                os.makedirs(
                    os.path.dirname(respaldo),
                    exist_ok=True
                )

                if not os.path.exists(respaldo):
                    shutil.copy2(ruta, respaldo)

            # -------------------------
            # Abrir imagen
            # -------------------------

            img = Image.open(ruta)

            # -------------------------
            # Corregir orientación EXIF
            # -------------------------

            img = ImageOps.exif_transpose(img)

            # -------------------------
            # Girar si quedó horizontal
            # -------------------------

            if img.width > img.height:

                img = img.rotate(
                    90,
                    expand=True
                )

                rotadas += 1

            # -------------------------
            # Eliminar transparencia
            # -------------------------

            if img.mode in ("RGBA", "LA"):

                fondo = Image.new(
                    "RGB",
                    img.size,
                    (255, 255, 255)
                )

                mascara = img.getchannel("A")

                fondo.paste(
                    img.convert("RGB"),
                    mask=mascara
                )

                img = fondo

                transparencias += 1

            elif img.mode == "P":

                img = img.convert("RGBA")

                fondo = Image.new(
                    "RGB",
                    img.size,
                    (255, 255, 255)
                )

                mascara = img.getchannel("A")

                fondo.paste(
                    img.convert("RGB"),
                    mask=mascara
                )

                img = fondo

                transparencias += 1

            else:

                img = img.convert("RGB")

            # -------------------------
            # Guardar
            # -------------------------

            extension = os.path.splitext(archivo)[1].lower()

            if extension in (".jpg", ".jpeg"):
                img.save(
                    ruta,
                    quality=95,
                    optimize=True
                )
            else:
                img.save(ruta)

            procesadas += 1

            print(f"OK -> {archivo}")

        except Exception as e:

            errores += 1

            print(f"ERROR -> {archivo}")
            print(e)

# ==========================================
# RESUMEN
# ==========================================

print("\n" + "=" * 40)
print("PROCESO FINALIZADO")
print("=" * 40)
print(f"Imágenes procesadas: {procesadas}")
print(f"Imágenes rotadas: {rotadas}")
print(f"Transparencias eliminadas: {transparencias}")
print(f"Errores: {errores}")
print("=" * 40)