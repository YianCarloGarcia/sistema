"""
recortar_carnet.py
------------------
Recorta fotos automáticamente para carnet (proporción 3:4, busto).
Usa OpenCV DNN — más preciso que Haar Cascades, sin depender de MediaPipe.

ESTRUCTURA DE CARPETAS:
  📁 tu-carpeta/
     📄 recortar_carnet.py
     📁 fotos_originales/      ← pon aquí los .jpg
     📁 fotos_recortadas/      ← resultados (se crea automáticamente)
     📁 fotos_no_detectadas/   ← fotos donde no se encontró cara

INSTALACIÓN (solo la primera vez):
  pip install opencv-python pillow numpy

USO:
  python recortar_carnet.py
"""

import os
import sys
import time
import shutil
import urllib.request

# ------------------------------------------------------------------
# Verificar librerías
# ------------------------------------------------------------------
try:
    import cv2
    from PIL import Image
    import numpy as np
except ImportError as e:
    print("=" * 60)
    print(f"ERROR: Falta una librería: {e}")
    print()
    print("Ejecuta este comando primero:")
    print()
    print("   pip install opencv-python pillow numpy")
    print()
    print("=" * 60)
    sys.exit(1)

# ------------------------------------------------------------------
# CONFIGURACIÓN — ajusta estos valores si el recorte no te convence
# ------------------------------------------------------------------

CARPETA_ENTRADA       = "fotos_originales"
CARPETA_SALIDA        = "fotos_recortadas"
CARPETA_NO_DETECTADAS = "fotos_no_detectadas"

# Tamaño final del recorte en píxeles (proporción 3:4)
ANCHO_SALIDA = 300
ALTO_SALIDA  = 400

# Márgenes alrededor de la cara detectada (fracción del tamaño de la cara)
# Aumenta MARGEN_INFERIOR para incluir más busto/hombros
MARGEN_LATERAL  = 0.8   # espacio a cada lado
MARGEN_SUPERIOR = 0.7   # espacio sobre la cabeza
MARGEN_INFERIOR = 2.2   # espacio bajo el mentón (busto y hombros)

# Confianza mínima del detector (0.0 a 1.0)
CONFIANZA_MINIMA = 0.5

EXTENSIONES = (".jpg", ".jpeg", ".png")

# ------------------------------------------------------------------
# Modelo DNN de OpenCV (se descarga automáticamente ~2.7 MB)
# ------------------------------------------------------------------
MODELO_DIR   = "modelo_cara"
MODELO_PROTO = os.path.join(MODELO_DIR, "deploy.prototxt")
MODELO_PESOS = os.path.join(MODELO_DIR, "res10_300x300_ssd_iter_140000.caffemodel")

URL_PROTO = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
URL_PESOS = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"


def descargar_modelo():
    os.makedirs(MODELO_DIR, exist_ok=True)
    if not os.path.exists(MODELO_PROTO):
        print("  📥 Descargando configuración del modelo...", end="", flush=True)
        try:
            urllib.request.urlretrieve(URL_PROTO, MODELO_PROTO)
            print(" ✅")
        except Exception as e:
            print(f" ❌ Error: {e}")
            sys.exit(1)
    if not os.path.exists(MODELO_PESOS):
        print("  📥 Descargando pesos del modelo (~2.7 MB)...", end="", flush=True)
        try:
            urllib.request.urlretrieve(URL_PESOS, MODELO_PESOS)
            print(" ✅")
        except Exception as e:
            print(f" ❌ Error: {e}")
            sys.exit(1)


def recortar_busto(img_pil, bbox, ancho_img, alto_img):
    x, y, w, h = bbox

    x1 = int(x - w * MARGEN_LATERAL)
    y1 = int(y - h * MARGEN_SUPERIOR)
    x2 = int(x + w + w * MARGEN_LATERAL)
    y2 = int(y + h + h * MARGEN_INFERIOR)

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(ancho_img, x2)
    y2 = min(alto_img, y2)

    ancho_recorte = x2 - x1
    alto_recorte  = y2 - y1

    if ancho_recorte <= 0 or alto_recorte <= 0:
        return None

    # Ajustar proporción 3:4
    proporcion = 3 / 4
    if ancho_recorte / alto_recorte > proporcion:
        nuevo_ancho = int(alto_recorte * proporcion)
        diff = (ancho_recorte - nuevo_ancho) // 2
        x1 += diff
        x2 -= diff
    else:
        nuevo_alto = int(ancho_recorte / proporcion)
        diff = nuevo_alto - alto_recorte
        y2 = min(alto_img, y2 + diff)
        alto_recorte = y2 - y1
        nuevo_alto   = int((x2 - x1) / proporcion)
        if nuevo_alto > alto_recorte:
            diff = nuevo_alto - alto_recorte
            y1   = max(0, y1 - diff)

    recorte = img_pil.crop((x1, y1, x2, y2))
    recorte = recorte.resize((ANCHO_SALIDA, ALTO_SALIDA), Image.LANCZOS)
    return recorte


def procesar_fotos():
    archivos = [
        f for f in os.listdir(CARPETA_ENTRADA)
        if f.lower().endswith(EXTENSIONES)
    ]

    if not archivos:
        print(f"\n  No se encontraron imágenes en '{CARPETA_ENTRADA}/'.")
        print("  Pon los archivos .jpg ahí y vuelve a ejecutar.")
        return

    total         = len(archivos)
    exitosos      = 0
    no_detectados = 0
    ya_procesados = 0

    print("=" * 60)
    print("  RECORTE AUTOMÁTICO PARA CARNET — OpenCV DNN")
    print("=" * 60)
    print(f"  Fotos encontradas : {total}")
    print(f"  Tamaño de salida  : {ANCHO_SALIDA}×{ALTO_SALIDA} px  (3:4)")
    print(f"  Carpeta salida    : {CARPETA_SALIDA}/")
    print(f"  Sin detección     : {CARPETA_NO_DETECTADAS}/")
    print("=" * 60)

    descargar_modelo()
    print()

    red = cv2.dnn.readNetFromCaffe(MODELO_PROTO, MODELO_PESOS)
    inicio_total = time.time()

    for i, nombre_archivo in enumerate(archivos, start=1):
        nombre_base   = os.path.splitext(nombre_archivo)[0]
        nombre_salida = nombre_base + ".jpg"

        ruta_entrada = os.path.join(CARPETA_ENTRADA, nombre_archivo)
        ruta_salida  = os.path.join(CARPETA_SALIDA, nombre_salida)
        ruta_no_det  = os.path.join(CARPETA_NO_DETECTADAS, nombre_archivo)

        if os.path.exists(ruta_salida):
            print(f"  [{i:>3}/{total}] ⏭  {nombre_archivo}  →  ya procesado")
            ya_procesados += 1
            continue

        print(f"  [{i:>3}/{total}] ⏳  {nombre_archivo} ...", end="", flush=True)
        inicio = time.time()

        try:
            img_cv = cv2.imread(ruta_entrada)
            if img_cv is None:
                raise ValueError("No se pudo leer la imagen")

            alto_img, ancho_img = img_cv.shape[:2]

            blob = cv2.dnn.blobFromImage(
                cv2.resize(img_cv, (300, 300)),
                1.0, (300, 300),
                (104.0, 177.0, 123.0)
            )
            red.setInput(blob)
            detecciones = red.forward()

            mejor_confianza = 0
            mejor_bbox      = None

            for k in range(detecciones.shape[2]):
                confianza = float(detecciones[0, 0, k, 2])
                if confianza > CONFIANZA_MINIMA and confianza > mejor_confianza:
                    mejor_confianza = confianza
                    x1 = int(detecciones[0, 0, k, 3] * ancho_img)
                    y1 = int(detecciones[0, 0, k, 4] * alto_img)
                    x2 = int(detecciones[0, 0, k, 5] * ancho_img)
                    y2 = int(detecciones[0, 0, k, 6] * alto_img)
                    mejor_bbox = (x1, y1, x2 - x1, y2 - y1)

            if mejor_bbox is None:
                shutil.copy2(ruta_entrada, ruta_no_det)
                duracion = time.time() - inicio
                print(f"  ⚠️   cara no detectada ({duracion:.1f}s) → {CARPETA_NO_DETECTADAS}/")
                no_detectados += 1
                continue

            img_pil = Image.open(ruta_entrada).convert("RGB")
            recorte = recortar_busto(img_pil, mejor_bbox, ancho_img, alto_img)

            if recorte is None:
                raise ValueError("El recorte quedó fuera de los límites de la imagen")

            recorte.save(ruta_salida, "JPEG", quality=95)
            duracion = time.time() - inicio
            print(f"  ✅  listo  (confianza: {mejor_confianza:.0%}, {duracion:.1f}s)")
            exitosos += 1

        except Exception as e:
            print(f"  ❌  ERROR: {e}")
            shutil.copy2(ruta_entrada, ruta_no_det)
            no_detectados += 1

    duracion_total = time.time() - inicio_total
    print()
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print(f"  ✅  Recortadas correctamente : {exitosos}")
    print(f"  ⏭   Ya procesadas antes      : {ya_procesados}")
    print(f"  ⚠️   Cara no detectada        : {no_detectados}")
    if no_detectados:
        print(f"       → Revísalas en '{CARPETA_NO_DETECTADAS}/'")
        print(f"         y recórtalas manualmente")
    print(f"  ⏱   Tiempo total             : {duracion_total:.1f}s")
    print(f"  📁  Resultados en            : {os.path.abspath(CARPETA_SALIDA)}/")
    print("=" * 60)


if __name__ == "__main__":
    os.makedirs(CARPETA_ENTRADA,       exist_ok=True)
    os.makedirs(CARPETA_SALIDA,        exist_ok=True)
    os.makedirs(CARPETA_NO_DETECTADAS, exist_ok=True)
    procesar_fotos()
