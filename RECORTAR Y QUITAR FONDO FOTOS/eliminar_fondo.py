"""
eliminar_fondo.py
-----------------
Elimina el fondo de un lote de fotos .jpg y guarda el resultado como .png
con fondo transparente.

USO:
  1. Pon este script en cualquier carpeta de tu computador.
  2. Crea una subcarpeta llamada "fotos_originales" y mete ahí los .jpg
  3. Abre una terminal en esa carpeta y ejecuta:
         python eliminar_fondo.py
  4. Los resultados quedarán en la carpeta "fotos_procesadas"

INSTALACIÓN (solo la primera vez):
  pip install rembg pillow onnxruntime

NOTA: La primera vez que ejecutes el script descargará automáticamente
un modelo de IA (~170 MB). Las siguientes veces ya no descarga nada.
"""

import os
import sys
import time

# ------------------------------------------------------------------
# Verificar que rembg y Pillow están instalados
# ------------------------------------------------------------------
try:
    from rembg import remove
    from PIL import Image
except ImportError:
    print("=" * 60)
    print("ERROR: Faltan librerías. Ejecuta este comando primero:")
    print()
    print(" python -m pip install rembg pillow onnxruntime")
    print()
    print("=" * 60)
    sys.exit(1)

# ------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------
CARPETA_ENTRADA  = "fotos_recortadas"   # Carpeta donde están los .jpg
CARPETA_SALIDA   = "fotos_procesadas"   # Carpeta donde se guardarán los .png
EXTENSIONES      = (".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG")

# ------------------------------------------------------------------
# Crear carpetas si no existen
# ------------------------------------------------------------------
os.makedirs(CARPETA_ENTRADA, exist_ok=True)
os.makedirs(CARPETA_SALIDA,  exist_ok=True)


def procesar_fotos():
    # Buscar todos los archivos de imagen en la carpeta de entrada
    archivos = [
        f for f in os.listdir(CARPETA_ENTRADA)
        if f.endswith(EXTENSIONES)
    ]

    if not archivos:
        print(f"\nNo se encontraron imágenes en la carpeta '{CARPETA_ENTRADA}'.")
        print("Asegúrate de poner los archivos .jpg ahí antes de ejecutar el script.")
        return

    total    = len(archivos)
    exitosos = 0
    fallidos = []

    print("=" * 60)
    print("  ELIMINADOR DE FONDOS — PROCESAMIENTO POR LOTE")
    print("=" * 60)
    print(f"  Fotos encontradas : {total}")
    print(f"  Carpeta entrada   : {CARPETA_ENTRADA}/")
    print(f"  Carpeta salida    : {CARPETA_SALIDA}/")
    print("=" * 60)
    print()

    inicio_total = time.time()

    for i, nombre_archivo in enumerate(archivos, start=1):
        # El archivo de salida tiene el mismo nombre pero extensión .png
        nombre_base  = os.path.splitext(nombre_archivo)[0]
        nombre_salida = nombre_base + ".png"

        ruta_entrada = os.path.join(CARPETA_ENTRADA, nombre_archivo)
        ruta_salida  = os.path.join(CARPETA_SALIDA,  nombre_salida)

        # Si ya fue procesado anteriormente, saltar
        if os.path.exists(ruta_salida):
            print(f"  [{i}/{total}] ⏭  {nombre_archivo}  →  ya procesado, saltando")
            exitosos += 1
            continue

        print(f"  [{i}/{total}] ⏳  {nombre_archivo} ...", end="", flush=True)
        inicio = time.time()

        try:
            # Abrir la imagen original
            with open(ruta_entrada, "rb") as f:
                datos_entrada = f.read()

            # Eliminar el fondo con rembg (IA)
            datos_salida = remove(datos_entrada)

            # Guardar como PNG con transparencia
            with open(ruta_salida, "wb") as f:
                f.write(datos_salida)

            duracion = time.time() - inicio
            print(f"  ✅  listo en {duracion:.1f}s")
            exitosos += 1

        except Exception as e:
            print(f"  ❌  ERROR: {e}")
            fallidos.append(nombre_archivo)

    # ------------------------------------------------------------------
    # Resumen final
    # ------------------------------------------------------------------
    duracion_total = time.time() - inicio_total
    print()
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print(f"  ✅  Procesadas correctamente : {exitosos}/{total}")
    if fallidos:
        print(f"  ❌  Con errores ({len(fallidos)}):")
        for f in fallidos:
            print(f"        - {f}")
    print(f"  ⏱   Tiempo total : {duracion_total:.1f} segundos")
    print(f"  📁  Resultados en : {os.path.abspath(CARPETA_SALIDA)}/")
    print("=" * 60)


if __name__ == "__main__":
    procesar_fotos()
