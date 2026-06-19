from rembg import remove
from PIL import Image, ImageOps
import os
import shutil
from io import BytesIO

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA_FOTOS = r"C:\Users\ycgar\Documentos\aplicacion\sistema\sistema\fotos\fotos"
CREAR_BACKUP = True

# ==========================================
# PROCESAR FOTO
# ==========================================

def procesar_foto(ruta):

    img = Image.open(ruta)

    # Corregir orientación EXIF
    img = ImageOps.exif_transpose(img)

    # Si quedó horizontal
    if img.width > img.height:
        img = img.rotate(90, expand=True)

    # Convertir a bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    # Eliminar fondo con IA
    salida = remove(buffer.getvalue())

    img_sin_fondo = Image.open(
        BytesIO(salida)
    ).convert("RGBA")

    # Fondo blanco
    fondo_blanco = Image.new(
        "RGB",
        img_sin_fondo.size,
        (255, 255, 255)
    )

    fondo_blanco.paste(
        img_sin_fondo,
        mask=img_sin_fondo.split()[3]
    )

    return fondo_blanco


# ==========================================
# BACKUP
# ==========================================

if CREAR_BACKUP:

    BACKUP = os.path.join(
        CARPETA_FOTOS,
        "_BACKUP"
    )

    os.makedirs(
        BACKUP,
        exist_ok=True
    )

# ==========================================
# RECORRER CARPETAS
# ==========================================

procesadas = 0
errores = 0

for raiz, _, archivos in os.walk(CARPETA_FOTOS):

    if "_BACKUP" in raiz:
        continue

    for archivo in archivos:

        if not archivo.lower().endswith(
            (".png", ".jpg", ".jpeg")
        ):
            continue

        ruta = os.path.join(
            raiz,
            archivo
        )

        try:

            # ----------------------
            # Backup
            # ----------------------

            if CREAR_BACKUP:

                destino = os.path.join(
                    BACKUP,
                    os.path.relpath(
                        ruta,
                        CARPETA_FOTOS
                    )
                )

                os.makedirs(
                    os.path.dirname(destino),
                    exist_ok=True
                )

                if not os.path.exists(destino):

                    shutil.copy2(
                        ruta,
                        destino
                    )

            # ----------------------
            # Procesar
            # ----------------------

            resultado = procesar_foto(ruta)

            # Guardar
            resultado.save(
                ruta,
                quality=95
            )

            procesadas += 1

            print(
                f"OK -> {archivo}"
            )

        except Exception as e:

            errores += 1

            print(
                f"ERROR -> {archivo}"
            )

            print(e)

print("\n" + "=" * 40)
print("PROCESO FINALIZADO")
print("=" * 40)
print(f"Procesadas : {procesadas}")
print(f"Errores    : {errores}")
print("=" * 40)