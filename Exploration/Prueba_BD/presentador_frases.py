"""Presentador de frases para la adquisición de voz de la base de datos (Obj. 3).

Hecho por Claude con la especificación del autor (2026-11-22). Es una utilidad de adquisición, no análisis del TT.
Diseño de la sesión: Metodologia/obj3_base_de_datos.md §4.1 (bloques b a f), §4.2 (sesión de niños), §4.3 y §4.5.

Flujo:
  0. Micrófono: se toma de config_audio.json, que escribe configurar_audio.py una vez por máquina (con prueba de
     nivel). Si no existe o el dispositivo ya no aparece, se elige aquí en la consola: dispositivo, prueba de nivel
     de 3 s por canal y canal del micrófono.
     La UMC202HD aparece como un par estéreo (IN 1-2): hay que elegir la entrada donde está el AT2020. El mismo
     aparato sale una vez por API; en Windows se usa WASAPI y el programa avisa si la entrada es otra (MME y
     DirectSound pasan por el mezclador de Windows, que puede remuestrear).
  1. Datos de la sesión (en la consola). El código se asigna solo (P01, P02…). Una sesión de prueba se guarda
     como P00, igual que las demás, pero no cuenta para el balance de listas, y sus datos se llenan solos
     (DATOS_PRUEBA). En las demás se pide la edad exacta (sin mínimo) y el grupo se deduce de ella.
     Sesión de niños (menores de 13, automática por la edad; decisión del 2026-11-27): silencio de referencia,
     imágenes y preguntas que dice el conductor, todo con voz normal. Sin calibración, frases, lectura, secuencias
     ni voz fuerte. Para probarla, la sesión de prueba pregunta si es de niños (o se da --ninos).
  2. Silencio de referencia (SILENCIO_REFERENCIA s), grabando, con una barra que muestra cuánto falta. Luego se muestra cómo se ve la barra de descanso.
  3. Calibración con calibracion.txt: el conductor presiona Espacio cuando la persona termina cada frase.
     Se mide el ritmo en segundos por sílaba.
  4. 6 listas de Lists_SHARVARD_MX, en orden mezclado:
       - fijas: LISTAS_FIJAS;
       - aleatorias: N_ALEATORIAS, balanceadas entre participantes, las menos usadas en asignaciones.csv, con
         semilla según el código.
     Cada frase se muestra sílabas × ritmo × MARGEN segundos, seguida de SILENCIO_FRASES s en blanco.
     Entre listas hay SILENCIO_LISTAS s de descanso, con una barra arriba que dice «Descanso» y se vacía con el tiempo.
     Mientras se lee, una barra delgada indica cuántas frases faltan para el siguiente descanso.
  5. Lectura continua (ARCHIVO_LECTURA, «El viento norte y el sol») y secuencias (SECUENCIAS: contar del 1 al 20 y
     los días de la semana). Cada una a su ritmo: el conductor presiona Espacio cuando la persona termina. Cada
     secuencia se dice en las dos VOCES, primero normal y luego fuerte. Cada secuencia sale primero con una barra
     de LECTURA_SECUENCIA s para leer qué decir, y luego el recuadro dice «¡Empieza ahora!» (Espacio adelanta ese
     momento); el tramo de lectura queda aparte en frases.csv (2026-11-27).
  6. Habla libre guiada (§4.3), cada bloque con una barra de tiempo:
       - imágenes (DURACION_IMAGENES s en cada voz): de la carpeta CARPETA_IMAGENES, en orden balanceado entre
         participantes (las menos usadas primero, con semilla según el código). Con Espacio se pasa a la siguiente;
       - preguntas (DURACION_PREGUNTAS s en cada voz): de preguntas.txt, en orden balanceado igual que las imágenes.
         Cada pregunta sale primero con una barra de LECTURA_PREGUNTA s para leerla, que no cuenta en el tiempo del
         bloque. Con Espacio se pasa a la siguiente.
     Desde las secuencias no hay barra de tiempo en pantalla (2026-11-27): el tiempo que queda sale solo en la línea
     del conductor.
     Antes de cada cambio de voz hay una pantalla de espera que lo explica y sirve de descanso (decisión del
     2026-11-25). Susurro y voz baja se quitaron el 2026-11-24: el lugar no se insonoriza lo suficiente.
     Las indicaciones y preguntas solo se muestran en pantalla (sin audio, decisión del 2026-11-22). Excepción, sesión
     de niños (2026-11-27): el conductor dice las preguntas en voz alta; esos tramos quedan aparte en frases.csv
     (pregunta_conductor y conductor).
     Lo que se lee en voz alta va en negro y sin recuadro. Las instrucciones y las preguntas van en un recuadro azul
     con título y otra letra (decisiones del 2026-11-24 y del 2026-11-25: el color solo no bastaba); cuando se pide
     voz fuerte, el recuadro va en rojo (2026-11-27). En las pantallas
     de espera se pide una seña con la mano al terminar de leer, para que el conductor sepa cuándo continuar.
  7. Guarda en CARPETA_SALIDA/<código>_<fecha>/ (Descargas/BD_VOZ, fuera de OneDrive; la copia al disco externo
     se hace aparte):
       audio.wav    48 kHz, 24 bits, una sola toma continua
       frases.csv   inicio y fin (s, en el reloj del audio) de cada frase, texto, secuencia, imagen o pregunta,
                    con su estilo, marca e interrupción
       sesion.json  datos de la sesión, entrada de audio, ritmo medido, listas, imágenes y preguntas mostradas,
                    duraciones y eventos (pausas y repeticiones)

Teclas (solo el conductor; la persona no debe tener el teclado):
  Espacio  calibración, lectura y secuencias: la persona terminó. Imágenes y preguntas: la siguiente.
           Espera: continuar. Si se deja presionada cuenta una sola vez
  P        pausa de emergencia. Otra vez para reanudar; la frase interrumpida se muestra de nuevo completa.
           En habla libre, el bloque sigue con el tiempo que le quedaba
  R        repite la frase, el texto o la secuencia actual (o la frase que acaba de terminar) por un ruido externo
           fuerte; la toma anterior queda en frases.csv con repetida = 1
  M        marca la frase, imagen o pregunta actual como dudosa (ruido externo, palabra omitida…)
  H        mantener presionada mientras habla el conductor: cada tramo queda en frases.csv (tipo «conductor») y, en
           imágenes y preguntas, el tiempo del bloque se detiene mientras tanto
  Esc      termina la sesión antes y guarda lo grabado
  F11      pantalla completa

Uso:
  python Exploration/Prueba_BD/presentador_frases.py              sesión normal
  python Exploration/Prueba_BD/presentador_frases.py --listar     lista los dispositivos de entrada
  python Exploration/Prueba_BD/presentador_frases.py --prueba     recorrido corto y automático, sin participante
  Opciones: --dispositivo N (índice de --listar), --sin-audio (no graba; para probar la pantalla),
            --ninos (sesión de prueba P00 de niños, sin preguntarlo; p. ej. con --prueba)
"""
import argparse
import csv
import datetime
import hashlib
import json
import random
import re
import sys
import time
import tkinter as tk
from collections import Counter
from pathlib import Path

import numpy as np

# ----------------------------------------------------------------- configuración
CARPETA = Path(__file__).resolve().parent
CARPETA_TEXTOS = CARPETA / "textos_prueba"       # listas, calibración, preguntas y lectura continua
ARCHIVO_LISTAS = CARPETA_TEXTOS / "Lists_SHARVARD_MX.txt"
ARCHIVO_CALIBRACION = CARPETA_TEXTOS / "calibracion.txt"
# Voces de personas: solo locales, fuera del repo y de OneDrive (decisión del 2026-11-22). En esta máquina es
# C:\Users\monit\Downloads\BD_VOZ; con Path.home() funciona igual en otra computadora.
CARPETA_SALIDA = Path.home() / "Downloads" / "BD_VOZ"
ARCHIVO_ASIGNACIONES = CARPETA_SALIDA / "asignaciones.csv"
ARCHIVO_PREGUNTAS = CARPETA_TEXTOS / "preguntas.txt"
ARCHIVO_LECTURA = CARPETA_TEXTOS / "El_viento_norte_y_el_sol.txt"   # versión de Coloma
CARPETA_IMAGENES = CARPETA / "image"             # no se versiona (Pexels); fuentes en textos_prueba/fuentes_imagenes.csv
ARCHIVO_CONFIG = CARPETA / "config_audio.json"   # lo escribe configurar_audio.py; es de cada máquina, no se versiona

LISTAS_FIJAS = (15, 33, 3)
N_ALEATORIAS = 3
MARGEN = 1.25                 # tiempo de cada frase = sílabas × ritmo de calibración × MARGEN
SILENCIO_FRASES = 2.0         # s en blanco después de cada frase
SILENCIO_LISTAS = 5.0         # s en blanco entre listas
SILENCIO_REFERENCIA = 30.0    # s de silencio grabado al inicio (ruido de fondo de la sesión)
VOCES = ("normal", "fuerte")  # en este orden, en las secuencias, las imágenes y las preguntas
DURACION_IMAGENES = 60.0      # s de imágenes en cada voz (las que alcancen)
DURACION_PREGUNTAS = 90.0     # s de preguntas en cada voz (sin contar la lectura de cada pregunta)
LECTURA_PREGUNTA = 5.0        # s con barra para leer cada pregunta antes de contestarla
LECTURA_SECUENCIA = 5.0       # s con barra para leer qué decir en cada secuencia, antes de «¡Empieza ahora!»
DURACION_IMAGENES_NINOS = 60.0   # sesión de niños: solo voz normal
DURACION_PREGUNTAS_NINOS = 90.0
EDAD_NINOS = 13               # menores de esta edad hacen la sesión de niños (grupo «niño»)
SECUENCIAS = (("numeros", "Cuenta del 1 al 20."),
              ("dias", "Di los días de la semana, de lunes a domingo."))

FS = 48000                    # Hz
BLOQUE = 1024                 # muestras por bloque de grabación
TAM_TEXTO = 40                # tamaño de las frases en pantalla
TAM_LECTURA = 36              # lectura continua: tamaño máximo; se reduce solo hasta que el texto quepa completo
TAM_AYUDA = 11                # línea de estado para el conductor
FUENTE_INSTRUCCION = "Georgia"  # distinta de la Arial de lo que se lee en voz alta
TAM_CONSIGNA = 26             # indicación arriba de la imagen, la pregunta o la lectura: tamaño máximo
PARTE_CONSIGNA = 0.28         # parte máxima del alto de la ventana para esa indicación
TAM_INSTRUCCION = 48          # pantallas de instrucciones: tamaño máximo, se reduce hasta que quepan
COLOR_LECTURA = "black"       # lo que la persona lee en voz alta
COLOR_INSTRUCCION = "#1f5f8b" # instrucciones, consignas y preguntas: no se leen en voz alta
FONDO_INSTRUCCION = "#eaf3fb"  # dentro del recuadro
COLOR_FUERTE = "#b0281c"      # el recuadro en rojo cuando se pide voz fuerte (2026-11-27)
FONDO_FUERTE = "#fbeceb"
COLOR_TEXTO_BARRA = "#143f5e" # texto sobre la barra de descanso o de tiempo

# Instrucciones de cada pantalla (las de las voces, las imágenes y las preguntas están en preguntas.txt)
INSTRUCCIONES = {
    "bienvenida": "Te damos la bienvenida.\n\n"
                  "En un recuadro azul (o rojo, cuando se pide voz fuerte) van las instrucciones y las "
                  "preguntas: no las leas en voz alta.\n"
                  "Lo que está en negro y sin recuadro sí se lee en voz alta.\n\n"
                  f"Primero grabaremos {SILENCIO_REFERENCIA:.0f} segundos del ruido del lugar.",
    "silencio": "No hables ni te muevas hasta que la barra se vacíe.",
    "barras": "Barra delgada: frases que faltan para descansar.\n\n"
              "Barra grande «Descanso»: no leas, espera a que se vacíe.",
    "calibracion": "Lee en voz alta cada frase en cuanto aparezca, con tu voz y ritmo normales.\n\n"
                   "Si te equivocas, no la repitas: continúa.",
    "frases": "Las frases cambiarán solas.\nLee cada una en voz alta, una sola vez.\n\n"
              "Con la pantalla en blanco, guarda silencio.",
    "lectura": "Lee en voz alta todo el texto, con tu voz y ritmo normales. Si te equivocas, continúa.",
    "secuencias": "Ahora no leerás.\n\nDi en voz alta lo que se pide, con tu voz normal.\n\n"
                  "Primero tendrás unos segundos para leer qué decir. Empieza cuando aparezca «¡Empieza ahora!».",
    "imagenes": "Ahora verás varias imágenes.\n\nDescríbelas en voz alta, con tu voz normal.",
    "preguntas": "Por último, contestarás varias preguntas con tu voz normal.\n\n"
                 "Primero tendrás unos segundos para leer cada pregunta. No la leas en voz alta. "
                 "No hay respuestas correctas.",
    "imagenes_nino": "Vas a ver unas imágenes.\n\nCuéntanos todo lo que ves, con tu voz normal.",
    "preguntas_nino": "Ahora te vamos a hacer unas preguntas.\n\nContesta con tu voz normal.",
    "pregunta_nino": "Escucha la pregunta y contesta con tu voz normal.",
    "cambio_fuerte": "Ahora lo mismo con voz fuerte, como si la persona estuviera al otro lado del salón.\n\n"
                     "No grites ni te acerques al micrófono.",
    "cambio_normal": "Ahora regresa a tu voz normal.",
    "pausa": "Pausa.\n\nNo hables hasta que cambie la pantalla.",
    "final": "Terminamos.\n\nMuchas gracias por participar.",
}
SENA = "Haz una seña con la mano cuando termines de leer."   # al pie de las pantallas de espera
EMPIEZA = "¡Empieza ahora!"   # título del recuadro de la secuencia cuando termina su barra de lectura
REPETICION_TECLA = 1.2        # s: más que el retardo máximo de repetición del teclado de Windows (1 s)

ALTO_BARRA = 34               # barra de descanso (px)
COLOR_BARRA = "#7fb3d5"
COLOR_PROGRESO = "#82c99a"    # barra delgada: cuánto falta para el siguiente descanso
CODIGO_PRUEBA = "P00"         # sesiones de prueba: se guardan normal, pero no cuentan para el balance de listas
# Datos de las sesiones de prueba: siempre los mismos, para no pedirlos (2026-11-25). La ganancia y el sonómetro van
# vacíos porque son mediciones: un valor fijo parecería real.
# El grupo de edad no va aquí: se deduce de la edad, como en las sesiones reales.
DATOS_PRUEBA = {"codigo": CODIGO_PRUEBA, "edad": 25, "sexo": "h", "lugar": "cubículo",
                "ganancia": "", "sonometro_fondo_dba": "", "conductor": "Arturo", "notas": "sesión de prueba"}
EDAD_PRUEBA_NINOS = 8         # edad de la sesión de prueba de niños
# Grupos de edad (edad mínima, nombre): se guarda la edad exacta y el grupo se deduce de ella
GRUPOS = ((60, "adulto mayor"), (31, "adulto"), (18, "adulto joven"), (13, "adolescente"), (0, "niño"))


# ----------------------------------------------------------------- textos
def leer_listas(ruta=ARCHIVO_LISTAS):
    """{número de lista: [10 frases]} desde el formato 'N<tab>LIST N' / 'k.<tab>frase'."""
    listas, actual = {}, None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\d+\tLIST (\d+)$", linea)
        if m:
            actual = int(m.group(1))
            listas[actual] = []
            continue
        m = re.match(r"^\d+\.\t(.+)$", linea)
        if m and actual is not None:
            listas[actual].append(m.group(1).strip())
    return listas


def leer_calibracion(ruta=ARCHIVO_CALIBRACION):
    return [l.strip() for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def leer_lectura(ruta=ARCHIVO_LECTURA):
    """Texto de la lectura continua en un solo párrafo; None si falta el archivo."""
    if not ruta.exists():
        return None
    return " ".join(ruta.read_text(encoding="utf-8").split())


def leer_preguntas(ruta=ARCHIVO_PREGUNTAS):
    """({id: texto} de las indicaciones, [(id, texto)] de las preguntas) desde secciones [x] con líneas 'id | texto'."""
    secciones, actual = {}, None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        m = re.fullmatch(r"\[(\w+)\]", linea)
        if m:
            actual = secciones.setdefault(m.group(1), [])
            continue
        clave, _, texto = linea.partition("|")
        if actual is None or not clave.strip() or not texto.strip():
            sys.exit(f"Línea mal formada en {ruta.name}: {linea}")
        actual.append((clave.strip(), texto.strip()))
    indicaciones = dict(secciones.get("indicaciones", []))
    faltan = {"imagen", "pregunta", *VOCES} - indicaciones.keys()
    if faltan or not secciones.get("preguntas"):
        sys.exit(f"{ruta.name} debe tener [indicaciones] con {sorted(faltan) or 'todas'} y al menos una pregunta"
                 " en [preguntas].")
    return indicaciones, secciones["preguntas"]


def leer_imagenes(carpeta=CARPETA_IMAGENES):
    if not carpeta.exists():
        return []
    return sorted(p.name for p in carpeta.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))


FUERTES, DEBILES_ACENTUADAS = set("aeoáéó"), set("íú")
VOCALES = FUERTES | set("iuü") | DEBILES_ACENTUADAS


def silabas(texto):
    """Número aproximado de sílabas: un núcleo por grupo de vocales, separando hiatos (dos fuertes, o í/ú)."""
    total = 0
    for palabra in re.findall(r"[a-záéíóúüñ]+", texto.lower()):
        if palabra == "y":  # la conjunción "y" es una sílaba
            total += 1
            continue
        previa = None
        for letra in palabra:
            if letra in VOCALES:
                if previa is None or (letra in FUERTES and previa in FUERTES) \
                        or letra in DEBILES_ACENTUADAS or previa in DEBILES_ACENTUADAS:
                    total += 1
                previa = letra
            else:
                previa = None
    return max(total, 1)


# ----------------------------------------------------------------- asignación de listas
def asignar_listas(codigo, todas, ruta=ARCHIVO_ASIGNACIONES):
    """Fijas más las N_ALEATORIAS menos usadas hasta ahora (empates al azar con semilla del código), en orden mezclado."""
    usos = Counter()
    if ruta.exists():
        with open(ruta, newline="", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                usos.update(int(x) for x in fila["listas_completas"].split() if x)
    rng = random.Random(int(hashlib.sha256(codigo.encode()).hexdigest(), 16))
    candidatas = [l for l in todas if l not in LISTAS_FIJAS]
    rng.shuffle(candidatas)  # desempate al azar, reproducible
    aleatorias = sorted(candidatas, key=lambda l: usos[l])[:N_ALEATORIAS]
    orden = list(LISTAS_FIJAS) + aleatorias
    rng.shuffle(orden)
    return orden, aleatorias


def balanceado(codigo, elementos, columna, ruta=ARCHIVO_ASIGNACIONES, clave=lambda x: x):
    """Los elementos, del menos usado al más usado según `columna` de asignaciones.csv (separados por ';'),
    con los empates al azar y una semilla según el código."""
    usos = Counter()
    if ruta.exists():
        with open(ruta, newline="", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                usos.update(x for x in (fila.get(columna) or "").split(";") if x)
    rng = random.Random(int(hashlib.sha256(f"{codigo}-{columna}".encode()).hexdigest(), 16))
    orden = list(elementos)
    rng.shuffle(orden)
    return sorted(orden, key=lambda e: usos[clave(e)])


def asignar_imagenes(codigo, imagenes):
    return balanceado(codigo, imagenes, "imagenes")


def asignar_preguntas(codigo, preguntas):
    return balanceado(codigo, preguntas, "preguntas", clave=lambda p: p[0])


# ----------------------------------------------------------------- grabación
def a_int32(datos, canales):
    """Bytes de 24 bits (paInt24, intercalados por canal) -> int32 (n, canales), con los 24 bits en la parte alta."""
    b = np.frombuffer(datos, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
    return ((b[:, 0] << 8) | (b[:, 1] << 16) | (b[:, 2] << 24)).reshape(-1, canales)


def nombre_dispositivo(info):
    nombre = info["name"]
    try:  # en Windows pyaudio a veces entrega los acentos mal decodificados
        nombre = nombre.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return nombre


def api_de(pa, indice):
    """Nombre de la API de audio del dispositivo (MME, WASAPI…): el mismo aparato aparece una vez por API."""
    return pa.get_host_api_info_by_index(pa.get_device_info_by_index(indice)["hostApi"])["name"]


def avisar_api(entrada):
    """En Windows, avisa si la entrada no es WASAPI: MME y DirectSound pasan por el mezclador, que puede remuestrear."""
    if sys.platform == "win32" and "WASAPI" not in (entrada.get("api") or ""):
        print(f"\n*** AVISO: «{entrada['nombre']}» usa {entrada.get('api') or 'una API desconocida'}, no WASAPI. Windows"
              " puede remuestrear o modificar el audio.\n    Elige la misma entrada en su versión «Windows WASAPI»"
              " (python Exploration/Prueba_BD/presentador_frases.py --listar). ***\n")


def localizar(pa, guardado, validos):
    """Índice actual de un dispositivo guardado. Los índices cambian al conectar o desconectar aparatos, así que se
    busca por nombre y API; None si ya no está o dejó de aceptar el formato."""
    if guardado["dispositivo"] in validos and validos[guardado["dispositivo"]] == guardado["nombre"] \
            and api_de(pa, guardado["dispositivo"]) == guardado.get("api"):
        return guardado["dispositivo"]
    return next((i for i, nombre in validos.items()
                 if nombre == guardado["nombre"] and api_de(pa, i) == guardado.get("api")), None)


def cargar_config(ruta=ARCHIVO_CONFIG):
    """(entrada, fecha) desde configurar_audio.py, con el índice actualizado; None si falta o no sirve."""
    if not ruta.exists():
        print(f"No hay configuración de audio guardada. Para no repetir este paso: "
              f"python Exploration/Prueba_BD/{ruta.with_name('configurar_audio.py').name}")
        return None
    import pyaudio
    config = json.loads(ruta.read_text(encoding="utf-8"))
    pa = pyaudio.PyAudio()
    try:
        entrada = dict(config["entrada"])
        i = localizar(pa, entrada, {v[0]: v[1] for v in dispositivos_validos(pa)})
        if i is None:
            print(f"La entrada guardada («{entrada['nombre']}», {entrada.get('api')}) no está conectada o ya no "
                  "acepta el formato. Conéctala o corre de nuevo configurar_audio.py.")
            return None
        entrada["dispositivo"] = i
    finally:
        pa.terminate()
    return entrada, config.get("fecha", "")


def dispositivos_validos(pa):
    """Entradas que aceptan FS y 24 bits: [(índice, nombre, canales)]."""
    import pyaudio
    validos = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] < 1:
            continue
        canales = min(int(info["maxInputChannels"]), 2)
        try:
            pa.is_format_supported(FS, input_device=i, input_channels=canales, input_format=pyaudio.paInt24)
        except ValueError:
            continue
        validos.append((i, nombre_dispositivo(info), canales))
    return validos


def prueba_de_nivel(pa, dispositivo, canales, segundos=3.0):
    """Graba unos segundos y devuelve el pico de cada canal en dBFS."""
    import pyaudio
    stream = pa.open(format=pyaudio.paInt24, channels=canales, rate=FS, input=True,
                     input_device_index=dispositivo, frames_per_buffer=BLOQUE)
    datos = b"".join(stream.read(BLOQUE, exception_on_overflow=False) for _ in range(int(segundos * FS / BLOQUE)))
    stream.stop_stream()
    stream.close()
    pico = np.abs(a_int32(datos, canales).astype(np.float64)).max(axis=0) / 2 ** 31
    return [20 * np.log10(max(v, 1e-9)) for v in pico]


def elegir_entrada(dispositivo=None):
    """En la consola: elegir el dispositivo, probar el nivel de cada canal y elegir el canal del micrófono."""
    import pyaudio
    pa = pyaudio.PyAudio()
    validos = dispositivos_validos(pa)
    if not validos:
        pa.terminate()
        sys.exit(f"No hay entradas que acepten {FS} Hz y 24 bits.")
    while True:
        if dispositivo is None:
            print(f"\nEntradas que aceptan {FS} Hz y 24 bits:")
            for i, nombre, canales in validos:
                print(f"  {i:>3}  {nombre}  ({canales} canal(es), {api_de(pa, i)})")
            r = input("Índice del dispositivo: ").strip()
            dispositivo = int(r) if r.isdigit() and int(r) in {v[0] for v in validos} else None
            if dispositivo is None:
                continue
        _, nombre, canales = next(v for v in validos if v[0] == dispositivo)
        avisar_api({"nombre": nombre, "api": api_de(pa, dispositivo)})
        input(f"Prueba de nivel en «{nombre}»: presiona Enter y habla al micrófono durante 3 s...")
        try:
            picos = prueba_de_nivel(pa, dispositivo, canales)
        except OSError as e:
            print(f"No se pudo abrir: {e}")
            dispositivo = None
            continue
        for k, db in enumerate(picos, start=1):
            barra = "#" * max(0, int((db + 60) / 2))  # de -60 dBFS (vacía) a 0 dBFS (30 marcas)
            print(f"  Canal {k} (entrada {k} de la interfaz): pico {db:6.1f} dBFS  {barra}")
        print("  Una voz normal a 15-20 cm debería quedar entre -30 y -6 dBFS. Si un canal queda cerca de -60,"
              " no le llega señal (revisa la entrada, el cable y los +48 V).")
        canal = 1
        if canales > 1:
            r = input("Canal del micrófono [1/2] (Enter = el de mayor nivel): ").strip()
            canal = int(r) if r in ("1", "2") else int(np.argmax(picos)) + 1
        r = input(f"¿Usar «{nombre}», canal {canal}? [s = sí / n = otro dispositivo / p = repetir la prueba]: ")
        r = r.strip().lower()
        if r == "s":
            api = api_de(pa, dispositivo)
            pa.terminate()
            return {"dispositivo": dispositivo, "nombre": nombre, "api": api, "canales": canales, "canal": canal,
                    "prueba_nivel_dbfs": [round(v, 1) for v in picos]}
        if r == "n":
            dispositivo = None


class Grabador:
    """Graba a FS y 24 bits con pyaudio y conserva solo el canal del micrófono. El reloj es el número de muestras."""

    def __init__(self, entrada):
        import pyaudio
        self.pa = pyaudio.PyAudio()
        self.canales, self.canal = entrada["canales"], entrada["canal"]
        self.bloques, self.muestras = [], 0
        self.stream = self.pa.open(format=pyaudio.paInt24, channels=self.canales, rate=FS, input=True,
                                   input_device_index=entrada["dispositivo"], frames_per_buffer=BLOQUE,
                                   stream_callback=self._recibir)

    def _recibir(self, datos, n, _info, _estado):
        import pyaudio
        self.bloques.append(datos)
        self.muestras += n
        return None, pyaudio.paContinue

    def tiempo(self):
        return self.muestras / FS

    def detener(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        return a_int32(b"".join(self.bloques), self.canales)[:, self.canal - 1]


class SinAudio:
    """Reloj de pared en lugar de grabación (para --sin-audio)."""

    def __init__(self):
        self.inicio = datetime.datetime.now()

    def tiempo(self):
        return (datetime.datetime.now() - self.inicio).total_seconds()

    def detener(self):
        return None


# ----------------------------------------------------------------- sesión
class Sesion:
    def __init__(self, datos, listas, calibracion, grabador, indicaciones, preguntas, imagenes, lectura=None,
                 prueba=False):
        self.datos, self.listas, self.calibracion, self.grab = datos, listas, calibracion, grabador
        self.indicaciones, self.preguntas, self.lectura = indicaciones, preguntas, lectura
        self.prueba = prueba
        escala = 0.15 if prueba else 1.0
        self.sil_ref, self.sil_frases, self.sil_listas = (SILENCIO_REFERENCIA * escala, SILENCIO_FRASES * escala,
                                                          SILENCIO_LISTAS * escala)
        escala_libre = 0.1 if prueba else 1.0
        self.nino = datos.get("grupo_edad") == "niño"
        self.dur_imagenes = (DURACION_IMAGENES_NINOS if self.nino else DURACION_IMAGENES) * escala_libre
        self.dur_preguntas = (DURACION_PREGUNTAS_NINOS if self.nino else DURACION_PREGUNTAS) * escala_libre
        self.dur_lectura = LECTURA_PREGUNTA * escala_libre
        self.dur_lectura_secuencia = LECTURA_SECUENCIA * escala_libre
        self.leyendo_secuencia = False   # True durante la barra de lectura de una secuencia
        self.orden, self.aleatorias = asignar_listas(datos["codigo"], sorted(listas))
        self.orden_imagenes = asignar_imagenes(datos["codigo"], imagenes)
        self.preguntas = asignar_preguntas(datos["codigo"], preguntas)
        if self.nino:
            self.orden, self.aleatorias = [], []
        if prueba:  # recorrido corto: 2 listas de 3 frases
            self.orden = self.orden[:2]
            self.calibracion = self.calibracion[:3]
        self.registro = []           # una fila por frase, texto, secuencia, imagen o pregunta
        self.eventos = []            # pausas, reanudaciones, repeticiones y fin anticipado
        self.duraciones_calib = []   # (segundos, sílabas)
        self.ritmo = None            # s por sílaba
        self.pasos, self.i, self.tarea, self.en_pausa = [], -1, None, False
        self.tras_frase = False      # True durante el silencio posterior a una frase ya leída
        self.fila_actual = None
        self.bloque = None           # habla libre en curso: tipo, voz y segundos que le quedan
        self.k_imagen = 0
        self.k_pregunta = 0
        self.foto = None             # referencia a la imagen mostrada (Tk la borra si no se guarda)
        self.hablando = None         # tramo en curso del conductor (tecla H)
        self.congelado = None        # tiempo del bloque detenido mientras habla el conductor
        self.texto_estado = ""
        self._auto_i, self._auto_id = None, None   # --prueba: cadena de Espacios automáticos

        self.raiz = tk.Tk()
        self.raiz.title("Presentador de frases")
        self.raiz.configure(bg="white")
        self.raiz.geometry("1200x700")
        # Barra de descanso arriba: se vacía conforme pasa el tiempo y dice "Descanso" (no es algo para leer)
        self.barra = tk.Canvas(self.raiz, height=ALTO_BARRA + 20, bg="white", highlightthickness=0)
        self.barra.pack(side="top", fill="x")
        self.barra_inicio = self.barra_total = self.barra_fin = None
        self.barra_visible = True
        # Indicación de la voz y la tarea, en un recuadro: aparece en la lectura y el habla libre
        self.consigna = tk.Frame(self.raiz, bg=FONDO_INSTRUCCION, highlightthickness=3,
                                 highlightbackground=COLOR_INSTRUCCION)
        self.titulo_consigna = tk.Label(self.consigna, text="INSTRUCCIONES",
                                        font=(FUENTE_INSTRUCCION, TAM_AYUDA + 3, "bold"), bg=COLOR_INSTRUCCION,
                                        fg="white", padx=12)
        self.titulo_consigna.pack(side="left", fill="y")
        self.texto_consigna = tk.Label(self.consigna, bg=FONDO_INSTRUCCION, fg=COLOR_INSTRUCCION, justify="center",
                                       padx=12, pady=4)
        self.texto_consigna.pack(side="left", expand=True, fill="both")
        # Zona central: lo que se lee en voz alta y las imágenes (texto), o un recuadro con título (caja)
        self.zona = tk.Frame(self.raiz, bg="white")
        self.zona.pack(expand=True, fill="both")
        self.zona.pack_propagate(False)
        self.texto = tk.Label(self.zona, text="", font=("Arial", TAM_TEXTO), bg="white", fg="black",
                              wraplength=1100, justify="center")
        self.caja = tk.Frame(self.zona, bg=FONDO_INSTRUCCION, highlightthickness=4,
                             highlightbackground=COLOR_INSTRUCCION)
        self.titulo_caja = tk.Label(self.caja, bg=COLOR_INSTRUCCION, fg="white", padx=20, pady=5)
        self.titulo_caja.pack(side="top", fill="x")
        self.texto_caja = tk.Label(self.caja, bg=FONDO_INSTRUCCION, fg=COLOR_INSTRUCCION, justify="center",
                                   padx=28, pady=14)
        self.texto_caja.pack(side="top", expand=True, fill="both")
        self.pie_caja = tk.Label(self.caja, text=SENA, bg=FONDO_INSTRUCCION, fg=COLOR_INSTRUCCION, padx=20, pady=8)
        self.zona.bind("<Configure>", lambda e: self.raiz.after_idle(self._reajustar_caja))  # p. ej. al presionar F11
        self.texto.pack(expand=True, fill="both")
        self.ayuda = tk.Label(self.raiz, text="", font=("Arial", TAM_AYUDA), bg="white", fg="gray60")
        self.ayuda.pack(side="bottom", fill="x")
        self.espacio_abajo, self.t_espacio = False, 0.0   # filtro de la repetición automática del teclado
        for tecla, accion in (("<KeyPress-space>", self.tecla_espacio), ("<KeyRelease-space>", self.soltar_espacio),
                              ("<p>", self.pausa), ("<P>", self.pausa),
                              ("<m>", self.marcar), ("<M>", self.marcar), ("<r>", self.repetir),
                              ("<R>", self.repetir), ("<Escape>", self.terminar),
                              ("<KeyPress-h>", self.hablar), ("<KeyPress-H>", self.hablar),
                              ("<KeyRelease-h>", self.callar), ("<KeyRelease-H>", self.callar),
                              ("<FocusOut>", self.callar),
                              ("<F11>", lambda e: self.raiz.attributes("-fullscreen",
                                                                       not self.raiz.attributes("-fullscreen")))):
            self.raiz.bind(tecla, accion)
        self.raiz.protocol("WM_DELETE_WINDOW", lambda: self.terminar(None))

        if self.nino:
            # Niños: sin lectura; imágenes y preguntas que dice el conductor, todo con voz normal
            self.pasos = [("espera", INSTRUCCIONES["bienvenida"]), ("silencio_ref", None)]
            if self.orden_imagenes:
                self.pasos += [("espera", INSTRUCCIONES["imagenes_nino"]), ("imagenes", "normal")]
            self.pasos += [("espera", INSTRUCCIONES["preguntas_nino"]), ("preguntas", "normal"),
                           ("espera", INSTRUCCIONES["final"])]
            self.siguiente()
            return
        self.pasos = [("espera", INSTRUCCIONES["bienvenida"]),
                      ("silencio_ref", None),
                      ("espera", INSTRUCCIONES["barras"]),
                      ("demo_descanso", None),
                      ("espera", INSTRUCCIONES["calibracion"])]
        self.pasos += [("calibracion", f) for f in self.calibracion]
        self.pasos += [("preparar_listas", None)]  # aquí se agregan las listas, ya con el ritmo medido
        self.siguiente()

    # ---- control
    def programar(self, segundos, funcion):
        self.tarea = self.raiz.after(int(segundos * 1000), funcion)

    def cancelar(self):
        if self.tarea is not None:
            self.raiz.after_cancel(self.tarea)
            self.tarea = None

    def estado(self, texto, reloj=None):
        """Línea gris del conductor. Con `reloj`, muestra además el tiempo que le queda al bloque."""
        self.texto_estado = texto
        extra = f"   ·   Quedan {self._reloj(reloj)}" if reloj is not None else ""
        self.ayuda.config(text=f"{texto}{extra}   |   Espacio · P pausa · R repetir · M marcar · H hablo (mantener) · "
                               "Esc terminar · F11 pantalla completa")

    def mostrar_barra(self, segundos, al_terminar, etiqueta="Descanso", total=None, visible=True):
        """Barra que se vacía en `segundos`. Con `total`, arranca ya gastada (para reanudar un bloque tras pausa).
        Sin `visible`, solo cuenta el tiempo y lo muestra en la línea del conductor."""
        total = total or segundos
        self.barra_inicio, self.barra_total, self.barra_fin = time.monotonic() - (total - segundos), total, al_terminar
        self.barra_etiqueta, self.barra_visible, self._segundo = etiqueta, visible, None
        if not visible:
            self.ocultar_barra()
        self._animar_barra()

    def barra_restante(self):
        return max(0.0, self.barra_total - (time.monotonic() - self.barra_inicio))

    def _animar_barra(self):
        transcurrido = time.monotonic() - self.barra_inicio
        if transcurrido >= self.barra_total:
            self.ocultar_barra()
            return self.barra_fin()
        if not self.barra_visible:
            segundo = round(self.barra_total - transcurrido)
            if segundo != self._segundo:  # la línea del conductor cambia una vez por segundo
                self._segundo = segundo
                self.estado(self.texto_estado, reloj=segundo)
            self.tarea = self.raiz.after(100, self._animar_barra)
            return
        ancho, margen = max(self.barra.winfo_width(), 400), 60
        lleno = (ancho - 2 * margen) * (1 - transcurrido / self.barra_total)
        self.barra.delete("all")
        self.barra.create_rectangle(margen, 10, ancho - margen, 10 + ALTO_BARRA, outline="gray70", width=2)
        self.barra.create_rectangle(margen, 10, margen + lleno, 10 + ALTO_BARRA, fill=COLOR_BARRA, outline="")
        self.barra.create_text(ancho / 2, 10 + ALTO_BARRA / 2, font=("Arial", TAM_AYUDA + 5),
                               fill=COLOR_TEXTO_BARRA,
                               text=f"{self.barra_etiqueta} · {self._reloj(self.barra_total - transcurrido)}")
        self.tarea = self.raiz.after(50, self._animar_barra)

    @staticmethod
    def _reloj(segundos):
        """'5 s' para descansos cortos; 'm:ss' a partir de un minuto."""
        s = round(segundos)
        return f"{s} s" if s < 60 else f"{s // 60}:{s % 60:02d}"

    def ocultar_barra(self):
        self.barra.delete("all")

    def dibujar_progreso(self, hechas, total, texto):
        """Barra delgada y discreta (distinta de la de descanso): avance hacia el siguiente descanso."""
        ancho, margen, y, alto = max(self.barra.winfo_width(), 400), 60, 12, 12
        self.barra.delete("all")
        self.barra.create_rectangle(margen, y, ancho - margen, y + alto, outline="gray80", width=1)
        self.barra.create_rectangle(margen, y, margen + (ancho - 2 * margen) * hechas / total, y + alto,
                                    fill=COLOR_PROGRESO, outline="")
        self.barra.create_text(ancho / 2, y + alto + 13, text=texto, font=("Arial", TAM_AYUDA + 1),
                               fill=COLOR_INSTRUCCION)

    def _texto_restantes(self, faltan, ultima):
        if faltan == 0:
            return "¡Terminamos las frases!" if ultima else "Ahora viene un descanso"
        destino = "terminar" if ultima else "el descanso"
        return f"Falta 1 frase para {destino}" if faltan == 1 else f"Faltan {faltan} frases para {destino}"

    def limpiar_pantalla(self):
        """Quita la imagen, la consigna y el recuadro (la frase se vuelve a escribir después)."""
        self.foto = None
        self.caja.place_forget()
        self.texto.config(image="", text="", font=("Arial", TAM_TEXTO), wraplength=1100)
        self.texto.pack(expand=True, fill="both")
        self.consigna.pack_forget()

    def pintar_recuadros(self, fuerte=False):
        """Azul normalmente; rojo cuando se pide voz fuerte."""
        color, fondo = (COLOR_FUERTE, FONDO_FUERTE) if fuerte else (COLOR_INSTRUCCION, FONDO_INSTRUCCION)
        for marco in (self.consigna, self.caja):
            marco.config(bg=fondo, highlightbackground=color)
        for titulo in (self.titulo_consigna, self.titulo_caja):
            titulo.config(bg=color)
        for texto in (self.texto_consigna, self.texto_caja, self.pie_caja):
            texto.config(bg=fondo, fg=color)

    def mostrar_instruccion(self, texto, titulo="INSTRUCCIONES", sena=False, fuerte=False):
        """Recuadro con título en el centro, para que no se confunda con una frase por leer. Con `sena`, al pie se
        pide la seña de que terminó de leer. Con `fuerte`, el recuadro va en rojo."""
        self.texto.pack_forget()
        self.pintar_recuadros(fuerte)
        self.titulo_caja.config(text=titulo)
        self.texto_caja.config(text=texto)
        self.pie_caja.pack_forget()
        if sena:
            self.pie_caja.pack(side="bottom", fill="x", before=self.texto_caja)
        self.caja.place(relx=0.5, rely=0.5, anchor="center")
        self._ajustar_caja()

    def _ajustar_caja(self, tam_min=14):
        """La letra más grande con la que el recuadro completo cabe en la zona central."""
        self.raiz.update_idletasks()
        if self.zona.winfo_height() <= 1:  # primera pantalla: la ventana todavía no se dibuja
            self.raiz.update()
        ancho, alto = self.zona.winfo_width() - 40, self.zona.winfo_height() - 20
        self.texto_caja.config(wraplength=max(ancho - 80, 300))
        for tam in range(TAM_INSTRUCCION, tam_min - 1, -1):
            self.texto_caja.config(font=(FUENTE_INSTRUCCION, tam))
            self.titulo_caja.config(font=(FUENTE_INSTRUCCION, max(int(tam * 0.55), 14), "bold"))
            self.pie_caja.config(font=(FUENTE_INSTRUCCION, max(int(tam * 0.65), 14), "bold italic"))
            self.raiz.update_idletasks()
            if self.caja.winfo_reqheight() <= alto and self.caja.winfo_reqwidth() <= ancho:
                break

    def _reajustar_caja(self):
        if self.caja.winfo_manager():
            self._ajustar_caja()

    def mostrar_consigna(self, texto, fuerte=False):
        """Recuadro de arriba, con la letra más grande que no pase de PARTE_CONSIGNA del alto de la ventana. Con
        `fuerte`, en rojo."""
        self.pintar_recuadros(fuerte)
        self.texto_consigna.config(text=texto)
        self.consigna.pack(side="top", fill="x", padx=12, pady=(4, 0), before=self.zona)
        self.raiz.update_idletasks()
        self.texto_consigna.config(wraplength=max(self.raiz.winfo_width() - 260, 600))
        for tam in range(TAM_CONSIGNA, 15, -1):
            self.texto_consigna.config(font=(FUENTE_INSTRUCCION, tam, "bold"))
            self.raiz.update_idletasks()
            if self.consigna.winfo_reqheight() <= PARTE_CONSIGNA * self.raiz.winfo_height():
                break

    def siguiente(self):
        self.cancelar()
        self.ocultar_barra()
        self.limpiar_pantalla()
        self.tras_frase = False
        self.bloque = None
        self.i += 1
        if self.i >= len(self.pasos):
            return self.finalizar()
        tipo, dato = self.pasos[self.i]
        getattr(self, f"_{tipo}")(dato)

    # ---- pasos
    def _espera(self, mensaje):
        self.mostrar_instruccion(mensaje, sena=mensaje != INSTRUCCIONES["final"],
                                 fuerte=mensaje == INSTRUCCIONES["cambio_fuerte"])
        self.estado("Esperando al conductor (Espacio)")
        if self.prueba:
            self.programar(0.5, self.siguiente)

    def _silencio_ref(self, _):
        self.mostrar_instruccion(INSTRUCCIONES["silencio"])
        self.estado(f"Silencio de referencia ({self.sil_ref:.0f} s)")
        self.fila_actual = self._fila("silencio_referencia", "", "", "")
        self.mostrar_barra(self.sil_ref, self._cerrar_y_seguir, etiqueta="Silencio")

    def _calibracion(self, frase):
        self.texto.config(text=frase, fg=COLOR_LECTURA)
        n = len([p for p in self.pasos[:self.i + 1] if p[0] == "calibracion"])
        self.estado(f"Calibración {n}/{len(self.calibracion)}: Espacio cuando termine de leer")
        self.fila_actual = self._fila("calibracion", "C", n, frase)
        total = len(self.calibracion)
        self.dibujar_progreso(n - 1, total, f"Frase {n} de {total}")
        if self.prueba:
            self.programar(0.4 + 0.05 * silabas(frase), lambda: self.espacio(None))

    def _preparar_listas(self, _):
        total_s = sum(d for d, _ in self.duraciones_calib)
        total_sil = sum(s for _, s in self.duraciones_calib)
        self.ritmo = total_s / total_sil if total_sil else 0.25
        nuevos = [("espera", INSTRUCCIONES["frases"])]
        for k, lista in enumerate(self.orden):
            if k:
                nuevos.append(("pausa_listas", None))
            nuevos += [("frase", (lista, num, frase)) for num, frase in enumerate(self.listas[lista], start=1)]
        # Lectura continua y secuencias (§4.1, bloques d y e): a su ritmo, Espacio al terminar
        if self.lectura:
            nuevos += [("espera", INSTRUCCIONES["lectura"]), ("lectura", self.lectura)]
        nuevos.append(("espera", INSTRUCCIONES["secuencias"]))
        for k, s in enumerate(SECUENCIAS):
            if k:
                nuevos.append(("espera", INSTRUCCIONES["cambio_normal"]))
            nuevos += self._en_cada_voz("secuencia", lambda voz, s=s: (*s, voz))
        # Habla libre guiada (§4.3): imágenes y preguntas, cada una con su barra de tiempo en cada voz
        if self.orden_imagenes:
            nuevos += [("espera", INSTRUCCIONES["imagenes"]), *self._en_cada_voz("imagenes")]
        nuevos += [("espera", INSTRUCCIONES["preguntas"]), *self._en_cada_voz("preguntas")]
        nuevos.append(("espera", INSTRUCCIONES["final"]))
        self.pasos[self.i + 1:self.i + 1] = nuevos
        print(f"Ritmo de lectura: {self.ritmo:.3f} s/sílaba. Listas: {self.orden} (aleatorias: {self.aleatorias})")
        self.siguiente()

    @staticmethod
    def _en_cada_voz(paso, dato=lambda voz: voz):
        """El paso en cada voz, con una pantalla de espera antes de cada cambio."""
        pasos = []
        for voz in VOCES:
            if pasos:
                pasos.append(("espera", INSTRUCCIONES[f"cambio_{voz}"]))
            pasos.append((paso, dato(voz)))
        return pasos

    def _frase(self, dato):
        lista, num, frase = dato
        duracion = silabas(frase) * self.ritmo * MARGEN
        self.texto.config(text=frase, fg=COLOR_LECTURA)
        k = self.orden.index(lista) + 1
        self.estado(f"Lista {lista} ({k}/{len(self.orden)}), frase {num}/10, {duracion:.1f} s")
        self.fila_actual = self._fila("frase", lista, num, frase)
        ultima = k == len(self.orden)
        n_lista = len(self.listas[lista])
        self.dibujar_progreso(num - 1, n_lista, self._texto_restantes(n_lista - num + 1, ultima))
        self.programar(duracion, lambda: self._fin_de_frase(num, n_lista, ultima))

    def _fin_de_frase(self, num, n_lista, ultima):
        self._cerrar_fila()
        self.dibujar_progreso(num, n_lista, self._texto_restantes(n_lista - num, ultima))
        self.tras_frase = True
        self.texto.config(text="")
        self.programar(self.sil_frases, self.siguiente)

    def _lectura(self, texto):
        self.mostrar_consigna(INSTRUCCIONES["lectura"])
        self.texto.config(text=texto, fg=COLOR_LECTURA)
        self._ajustar_letra(TAM_LECTURA)
        self.estado("Lectura continua: Espacio cuando termine de leer")
        self.fila_actual = self._fila("lectura", "", ARCHIVO_LECTURA.stem, texto)
        if self.prueba:
            self.programar(1.5, lambda: self.espacio(None))

    def _ajustar_letra(self, tam_max, tam_min=12):
        """Reduce la letra hasta que el texto completo quepa en la pantalla (depende de la escala de Windows)."""
        self.raiz.update_idletasks()
        disponible = self.zona.winfo_height()
        self.texto.config(wraplength=max(int(self.zona.winfo_width() * 0.8), 600))  # renglones legibles
        for tam in range(tam_max, tam_min - 1, -1):
            self.texto.config(font=("Arial", tam))
            self.raiz.update_idletasks()
            if self.texto.winfo_reqheight() <= disponible:
                break

    def _secuencia(self, dato):
        """Primero una barra para leer qué decir (como en las preguntas) y luego «¡Empieza ahora!» (2026-11-27)."""
        clave, consigna, voz = dato
        self.leyendo_secuencia = True
        self.mostrar_instruccion(f"{self.indicaciones[voz]}\n\n{consigna}", fuerte=voz == "fuerte")
        self.estado(f"Secuencia «{clave}» ({voz}): leyendo. Espacio = empezar ya")
        self.fila_actual = self._fila("leer_secuencia", "", clave, consigna, estilo="")
        self.mostrar_barra(self.dur_lectura_secuencia, lambda: self._empezar_secuencia(dato), etiqueta="Lee qué decir")

    def _empezar_secuencia(self, dato):
        """Termina la lectura: el recuadro dice que empiece y desde aquí se registra la secuencia."""
        clave, consigna, voz = dato
        self.cancelar()
        self.ocultar_barra()
        self.leyendo_secuencia = False
        self._cerrar_fila()
        self.mostrar_instruccion(f"{self.indicaciones[voz]}\n\n{consigna}", titulo=EMPIEZA.upper(),
                                 fuerte=voz == "fuerte")
        self.estado(f"Secuencia «{clave}» ({voz}): Espacio cuando termine")
        self.fila_actual = self._fila("secuencia", "", clave, consigna, estilo=voz)
        if self.prueba:
            self.programar(1.0, lambda: self.espacio(None))

    def _pausa_listas(self, _):
        self.texto.config(text="")
        self.estado(f"Descanso entre listas ({self.sil_listas:.0f} s)")
        self.mostrar_barra(self.sil_listas, self.siguiente)

    def _demo_descanso(self, _):
        self.texto.config(text="")
        self.estado("Demostración de la barra de descanso")
        self.mostrar_barra(self.sil_listas, self.siguiente)

    # ---- habla libre guiada: un bloque con tiempo fijo; Espacio cambia de imagen o de pregunta
    def _imagenes(self, voz):
        self._bloque("imagen", voz, self.dur_imagenes)

    def _preguntas(self, voz):
        self._bloque("pregunta", voz, self.dur_preguntas)

    def _bloque(self, tipo, voz, duracion):
        self.bloque = {"tipo": tipo, "voz": voz, "restante": duracion, "total": duracion, "fase": None}
        self._correr_bloque()

    def _correr_bloque(self):
        """Muestra el elemento actual y arranca (o retoma) el tiempo del bloque. Las preguntas de los adultos
        empiezan con su barra de lectura, que no cuenta en ese tiempo."""
        b = self._mostrar_elemento()
        if b["tipo"] == "pregunta" and not self.nino:
            b["fase"] = "leer"
            self.mostrar_barra(self.dur_lectura, self._empezar_respuesta, etiqueta="Lee la pregunta")
        else:
            self._contar_bloque()
        if self.prueba and self._auto_i != self.i:  # una sola cadena por bloque
            self._auto_i = self.i
            self._auto_espacio(self.i)

    def _contar_bloque(self):
        """Tiempo del bloque sin barra en pantalla: solo lo ve el conductor."""
        b = self.bloque
        b["fase"] = "contestar"
        self.mostrar_barra(b["restante"], self._fin_bloque, etiqueta="Tiempo", total=b["total"], visible=False)

    def _empezar_respuesta(self):
        """Termina la lectura de la pregunta: desde aquí corre el tiempo y se registra la respuesta."""
        self._cerrar_fila()
        clave, pregunta = self.preguntas[self.k_pregunta % len(self.preguntas)]
        self.fila_actual = self._fila("pregunta", "", clave, pregunta, estilo=self.bloque["voz"])
        self.estado(f"Pregunta {clave} ({self.bloque['voz']}): contestando. Espacio = siguiente pregunta")
        self._contar_bloque()

    def _auto_espacio(self, i):
        """--prueba: pasa de imagen o de pregunta sola."""
        def paso():
            if self.i != i or self.en_pausa or self.bloque is None:
                return
            self.espacio(None)
            self._auto_id = self.raiz.after(2500, paso)
        self._auto_id = self.raiz.after(2500, paso)

    def _mostrar_elemento(self):
        """Imagen o pregunta actual en pantalla y fila nueva en el registro."""
        b = self.bloque
        self.limpiar_pantalla()
        if b["tipo"] == "pregunta" and self.nino:  # la pregunta la dice el conductor
            n = self.k_pregunta + 1
            self.mostrar_instruccion(INSTRUCCIONES["pregunta_nino"], titulo="PREGUNTA")
            self.fila_actual = self._fila("pregunta_conductor", "", n, "", estilo=b["voz"])
            self.estado(f"Pregunta {n}: dila manteniendo H. Espacio = siguiente pregunta")
            return b
        # primero la voz que se pide y debajo la tarea
        fuerte = b["voz"] == "fuerte"
        self.mostrar_consigna(f"{self.indicaciones[b['voz']]}\n{self.indicaciones[b['tipo']]}", fuerte=fuerte)
        if b["tipo"] == "imagen":
            nombre = self.orden_imagenes[self.k_imagen % len(self.orden_imagenes)]
            self._dibujar_imagen(nombre)
            self.fila_actual = self._fila("imagen", "", self.k_imagen + 1, nombre, estilo=b["voz"])
            self.estado(f"Imagen {self.k_imagen + 1} ({b['voz']}): {nombre}. Espacio = siguiente imagen")
        else:
            clave, pregunta = self.preguntas[self.k_pregunta % len(self.preguntas)]
            self.mostrar_instruccion(pregunta, titulo="PREGUNTA", fuerte=fuerte)
            # mientras la lee, la persona no debería hablar; el tramo queda aparte, sin estilo
            self.fila_actual = self._fila("leer_pregunta", "", clave, pregunta, estilo="")
            self.estado(f"Pregunta {clave} ({b['voz']}): leyendo. Espacio = siguiente pregunta")
        return b

    def _dibujar_imagen(self, nombre):
        from PIL import Image, ImageOps, ImageTk
        self.raiz.update_idletasks()
        ancho = max(self.zona.winfo_width(), 600) - 40
        alto = max(self.zona.winfo_height(), 200) - 20
        with Image.open(CARPETA_IMAGENES / nombre) as im:
            im.draft("RGB", (max(ancho, alto),) * 2)  # decodifica el JPEG ya reducido: mucho más rápido
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((ancho, alto))
        self.foto = ImageTk.PhotoImage(im)
        self.texto.config(image=self.foto, text="")

    def _siguiente_elemento(self):
        self._cerrar_fila()
        self._avanzar_elemento()
        if self.bloque["tipo"] == "pregunta" and not self.nino:
            # la nueva pregunta vuelve a tener su lectura; el tiempo del bloque se detiene mientras tanto
            if self.bloque["fase"] == "contestar":
                self.bloque["restante"] = self.barra_restante()
            self.cancelar()
            self._correr_bloque()
        else:
            self._mostrar_elemento()

    def _avanzar_elemento(self):
        if self.bloque["tipo"] == "imagen":
            self.k_imagen += 1
        else:
            self.k_pregunta += 1

    def _fin_bloque(self):
        self._cerrar_fila()
        self._avanzar_elemento()   # la siguiente voz empieza con otra imagen o pregunta
        self.siguiente()

    # ---- registro
    def _fila(self, tipo, lista, num, texto, estilo="normal"):
        """Una fila de frases.csv. En habla libre, «frase» es el número de imagen o el id de la pregunta; en la
        lectura continua, el nombre del texto, y en las secuencias, su clave."""
        lectura = tipo in ("frase", "calibracion", "lectura")
        return {"tipo": tipo, "lista": lista, "frase": num, "texto": texto,
                "silabas": silabas(texto) if lectura else "", "estilo": estilo if tipo != "silencio_referencia" else "",
                "inicio_s": round(self.grab.tiempo(), 3), "fin_s": "", "marcada": 0, "interrumpida": 0,
                "repetida": 0}

    def _cerrar_fila(self, interrumpida=False, repetida=False):
        if self.fila_actual is None:
            return
        self.fila_actual["fin_s"] = round(self.grab.tiempo(), 3)
        self.fila_actual["interrumpida"] = int(interrumpida)
        self.fila_actual["repetida"] = int(repetida)
        self.registro.append(self.fila_actual)
        self.fila_actual = None

    def _cerrar_y_seguir(self):
        self._cerrar_fila()
        self.siguiente()

    # ---- teclas
    def tecla_espacio(self, evento):
        """Windows repite la tecla mientras está presionada, y eso saltaba pasos: cada pulsación cuenta una vez. El
        tiempo límite evita que Espacio quede bloqueado si la ventana pierde el foco antes de soltarlo."""
        ahora = time.monotonic()
        repeticion = self.espacio_abajo and ahora - self.t_espacio < REPETICION_TECLA
        self.espacio_abajo, self.t_espacio = True, ahora
        if not repeticion:
            self.espacio(evento)

    def soltar_espacio(self, _evento):
        self.espacio_abajo = False

    def hablar(self, _evento):
        """H presionada: empieza un tramo del conductor. En imágenes y preguntas, el tiempo se detiene."""
        if self.hablando is not None or self.i >= len(self.pasos):
            return  # repetición automática del teclado
        self.hablando = self._fila("conductor", "", "", "", estilo="")
        if self.bloque is not None and not self.en_pausa and self.tarea is not None:
            self.congelado = (self.barra_restante(), self.barra_fin, self.barra_etiqueta, self.barra_total,
                              self.barra_visible)
            self.cancelar()
        self.estado(f"HABLANDO EL CONDUCTOR (suelta H al terminar) · {self.texto_estado}")

    def callar(self, _evento):
        """H soltada (o la ventana perdió el foco): termina el tramo y el tiempo sigue donde se quedó."""
        if self.hablando is None:
            return
        self.hablando["fin_s"] = round(self.grab.tiempo(), 3)
        self.registro.append(self.hablando)
        self.hablando = None
        self.estado(self.texto_estado.split(" · ", 1)[-1] if self.texto_estado.startswith("HABLANDO") else
                    self.texto_estado)
        if self.congelado is not None:
            restante, fin, etiqueta, total, visible = self.congelado
            self.congelado = None
            if not self.en_pausa:
                self.mostrar_barra(restante, fin, etiqueta=etiqueta, total=total, visible=visible)

    def espacio(self, _evento):
        if self.en_pausa or self.i >= len(self.pasos):
            return
        self.callar(None)
        tipo, frase = self.pasos[self.i]
        if tipo == "espera":
            self.siguiente()
        elif self.bloque is not None:
            self._siguiente_elemento()
        elif tipo == "calibracion":
            inicio = self.fila_actual["inicio_s"]
            self._cerrar_fila()
            self.duraciones_calib.append((self.registro[-1]["fin_s"] - inicio, silabas(frase)))
            self.siguiente()
        elif tipo == "secuencia" and self.leyendo_secuencia:  # ya leyó: empieza sin esperar la barra
            self._empezar_secuencia(frase)
        elif tipo in ("lectura", "secuencia"):
            self._cerrar_y_seguir()

    def pausa(self, _evento):
        if self.i >= len(self.pasos):
            return
        if not self.en_pausa:
            self.callar(None)
            self.en_pausa = True
            # habla libre: al reanudar sigue con el tiempo que le quedaba (la lectura de la pregunta se repite)
            if self.bloque is not None and self.bloque["fase"] == "contestar":
                self.bloque["restante"] = self.barra_restante()
            self.cancelar()
            self.ocultar_barra()
            self.limpiar_pantalla()
            if self.fila_actual is not None:
                self._cerrar_fila(interrumpida=True)
            self.eventos.append({"evento": "pausa", "t_s": round(self.grab.tiempo(), 3)})
            self.mostrar_instruccion(INSTRUCCIONES["pausa"])
            self.estado("PAUSA: P para reanudar (la frase interrumpida se repite completa)")
        else:
            self.en_pausa = False
            self.eventos.append({"evento": "reanudacion", "t_s": round(self.grab.tiempo(), 3)})
            if self.bloque is not None:  # misma imagen o pregunta, con el tiempo que le quedaba
                self._correr_bloque()
            elif self.tras_frase:  # la frase ya se había leído completa: sigue con la próxima
                self.siguiente()
            else:
                self.limpiar_pantalla()  # quita el recuadro de la pausa
                tipo, dato = self.pasos[self.i]
                getattr(self, f"_{tipo}")(dato)  # repite el paso actual desde el inicio

    def repetir(self, _evento):
        """Repite la frase, el texto o la secuencia actual (o la frase que acaba de terminar) por un ruido externo
        fuerte. La toma anterior queda en frases.csv con repetida = 1, para descartarla al etiquetar."""
        if self.en_pausa or self.i >= len(self.pasos):
            return
        tipo, dato = self.pasos[self.i]
        if tipo not in ("frase", "calibracion", "lectura", "secuencia"):
            return
        self.cancelar()
        if self.fila_actual is not None:
            self._cerrar_fila(repetida=True)
        elif self.tras_frase and self.registro:
            self.registro[-1]["repetida"] = 1
        self.tras_frase = False
        if tipo == "frase":
            lista, frase = dato[0], dato[1]
        elif tipo == "calibracion":
            lista, frase = "C", ""
        else:  # lectura o secuencia
            lista, frase = "", ARCHIVO_LECTURA.stem if tipo == "lectura" else dato[0]
        self.eventos.append({"evento": "repeticion", "t_s": round(self.grab.tiempo(), 3), "lista": lista,
                             "frase": frase, "estilo": dato[2] if tipo == "secuencia" else "normal"})
        self.estado("Repitiendo")
        getattr(self, f"_{tipo}")(dato)

    def marcar(self, _evento):
        if self.fila_actual is not None:
            self.fila_actual["marcada"] = 1
        elif self.registro:  # durante el silencio posterior: marca la frase que acaba de terminar
            self.registro[-1]["marcada"] = 1
        self.estado("Frase marcada")

    def terminar(self, _evento):
        self.callar(None)
        self.eventos.append({"evento": "fin_anticipado", "t_s": round(self.grab.tiempo(), 3)})
        self._cerrar_fila(interrumpida=True)
        self.finalizar()

    # ---- cierre
    def finalizar(self):
        self.callar(None)  # cierra el tramo del conductor si H sigue presionada
        self.cancelar()
        if self._auto_id is not None:
            self.raiz.after_cancel(self._auto_id)
        audio = self.grab.detener()
        carpeta = CARPETA_SALIDA / f"{self.datos['codigo']}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        carpeta.mkdir(parents=True, exist_ok=True)
        if audio is not None:
            import soundfile
            soundfile.write(carpeta / "audio.wav", audio, FS, subtype="PCM_24")
        self.registro.sort(key=lambda r: r["inicio_s"])
        with open(carpeta / "frases.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["tipo", "lista", "frase", "texto", "silabas", "estilo", "inicio_s", "fin_s",
                                   "marcada", "interrumpida", "repetida"])
            w.writeheader()
            w.writerows(self.registro)
        completas = [l for l in self.orden  # cada frase de la lista con al menos una toma válida
                     if len({r["frase"] for r in self.registro if r["lista"] == l and not r["interrumpida"]
                             and not r["repetida"]}) == len(self.listas[l])]
        mostradas = list(dict.fromkeys(r["texto"] for r in self.registro if r["tipo"] == "imagen"))
        hechas = list(dict.fromkeys(r["frase"] for r in self.registro if r["tipo"] == "pregunta"))
        sesion = dict(self.datos, fecha=datetime.datetime.now().isoformat(timespec="seconds"), prueba=self.prueba,
                      tipo_sesion="niños" if self.nino else "adultos", lectura_pregunta_s=self.dur_lectura,
                      lectura_secuencia_s=self.dur_lectura_secuencia,
                      ritmo_s_por_silaba=self.ritmo, margen=MARGEN, silencio_frases_s=self.sil_frases,
                      silencio_listas_s=self.sil_listas, silencio_referencia_s=self.sil_ref,
                      listas_orden=self.orden, listas_fijas=list(LISTAS_FIJAS), listas_aleatorias=self.aleatorias,
                      listas_completas=completas, imagenes_mostradas=mostradas, preguntas_mostradas=hechas,
                      voces=["normal"] if self.nino else list(VOCES), duracion_imagenes_por_voz_s=self.dur_imagenes,
                      duracion_preguntas_por_voz_s=self.dur_preguntas, eventos=self.eventos, fs=FS, bits=24,
                      archivo_listas=ARCHIVO_LISTAS.name, archivo_calibracion=ARCHIVO_CALIBRACION.name,
                      archivo_preguntas=ARCHIVO_PREGUNTAS.name,
                      archivo_lectura=ARCHIVO_LECTURA.name if self.lectura else None,
                      secuencias=[] if self.nino else [c for c, _ in SECUENCIAS])
        (carpeta / "sesion.json").write_text(json.dumps(sesion, ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.prueba and self.datos["codigo"] != CODIGO_PRUEBA:  # las pruebas no cuentan para el balance
            nuevo = not ARCHIVO_ASIGNACIONES.exists()
            with open(ARCHIVO_ASIGNACIONES, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if nuevo:
                    w.writerow(["codigo", "fecha", "listas_completas", "imagenes", "preguntas"])
                w.writerow([self.datos["codigo"], sesion["fecha"], " ".join(map(str, completas)),
                            ";".join(mostradas), ";".join(hechas)])
        print(f"Guardado en {carpeta}")
        self.raiz.destroy()


# ----------------------------------------------------------------- consola
def grupo_de_edad(edad):
    return next(nombre for minima, nombre in GRUPOS if edad >= minima)


def siguiente_codigo():
    """El siguiente código libre (P01, P02…), según asignaciones.csv y las carpetas ya guardadas; P00 no cuenta."""
    usados = set()
    if ARCHIVO_ASIGNACIONES.exists():
        with open(ARCHIVO_ASIGNACIONES, newline="", encoding="utf-8") as f:
            usados.update(fila["codigo"] for fila in csv.DictReader(f))
    if CARPETA_SALIDA.exists():
        usados.update(d.name.split("_")[0] for d in CARPETA_SALIDA.iterdir() if d.is_dir())
    numeros = [int(c[1:]) for c in usados if re.fullmatch(r"P\d+", c) and c != CODIGO_PRUEBA]
    return f"P{max(numeros, default=0) + 1:02d}"


def datos_prueba(ninos=False):
    """Los datos fijos de P00; con `ninos`, la edad de niño, y el grupo siempre se deduce de la edad."""
    datos = dict(DATOS_PRUEBA)
    if ninos:
        datos["edad"] = EDAD_PRUEBA_NINOS
    datos["grupo_edad"] = grupo_de_edad(datos["edad"])
    tipo = "de niños" if datos["grupo_edad"] == "niño" else "de adultos"
    print(f"Código asignado: {CODIGO_PRUEBA}, sesión {tipo}. Datos de prueba: {datos['edad']} años, sexo "
          f"{datos['sexo']}, {datos['lugar']}, conductor {datos['conductor']}.")
    return datos


def pedir_datos(ninos=None):
    """Con `ninos` (opción --ninos) no se pregunta si la prueba es de niños."""
    def opcion(pregunta, opciones):
        while True:
            r = input(f"{pregunta} {list(opciones)}: ").strip().lower()
            if r in opciones:
                return r
    prueba = opcion(f"¿Es una sesión de prueba? (se guarda como {CODIGO_PRUEBA})", ("s", "n")) == "s"
    if prueba:
        if ninos is None:
            ninos = opcion(f"¿Prueba de niños? ({EDAD_PRUEBA_NINOS} años)", ("s", "n")) == "s"
        return datos_prueba(ninos)
    if ninos:
        print("AVISO: --ninos solo aplica a sesiones de prueba (P00); se usa la edad capturada.")
    codigo = siguiente_codigo()
    print(f"Código asignado: {codigo}")
    edad = None
    while edad is None:
        r = input("Edad (años): ").strip()
        edad = int(r) if r.isdigit() and 1 <= int(r) <= 110 else None  # sin edad mínima (decisión del 2026-11-27)
    if grupo_de_edad(edad) == "niño":
        print(f"Menor de {EDAD_NINOS} años: sesión de niños (imágenes y preguntas que dices tú, solo voz normal).")
    return {"codigo": codigo, "edad": edad, "grupo_edad": grupo_de_edad(edad),
            "sexo": opcion("Sexo", ("h", "m")),
            "lugar": opcion("Lugar", ("cubículo", "auto")),
            "ganancia": input("Ganancia de la interfaz (como la anotas): ").strip(),
            "sonometro_fondo_dba": input("Sonómetro, ruido de fondo en dB(A): ").strip(),
            "conductor": input("Conductor: ").strip(),
            "notas": input("Notas: ").strip()}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--listar", action="store_true", help="lista los dispositivos de entrada y sale")
    p.add_argument("--dispositivo", type=int, default=None,
                   help="índice del dispositivo de entrada (si no se da, se elige en la consola)")
    p.add_argument("--prueba", action="store_true", help="recorrido corto y automático")
    p.add_argument("--sin-audio", action="store_true", help="no graba (solo prueba la pantalla)")
    p.add_argument("--ninos", action="store_true", help="en una sesión de prueba (P00), usar la sesión de niños")
    a = p.parse_args()
    if a.listar:
        import pyaudio
        pa = pyaudio.PyAudio()
        validos = {v[0] for v in dispositivos_validos(pa)}
        print("Entradas:")
        for i in range(pa.get_device_count()):
            d = pa.get_device_info_by_index(i)
            if d["maxInputChannels"] > 0:
                marca = "OK" if i in validos else "--"
                print(f"{i:>3} [{marca}] {nombre_dispositivo(d)}  ({int(d['defaultSampleRate'])} Hz, {api_de(pa, i)})")
        print(f"[OK] = acepta {FS} Hz y 24 bits. En Windows, usar la entrada «Windows WASAPI» de la interfaz.")
        pa.terminate()
        return
    listas, calibracion = leer_listas(), leer_calibracion()
    indicaciones, preguntas = leer_preguntas()
    imagenes = leer_imagenes()
    if not imagenes:
        print(f"AVISO: no hay imágenes en {CARPETA_IMAGENES}; se omite el bloque de imágenes.")
    lectura = leer_lectura()
    if not lectura:
        print(f"AVISO: no existe {ARCHIVO_LECTURA}; se omite la lectura continua.")
    entrada = None
    if not a.sin_audio:
        # Con la configuración guardada no se pregunta nada; --dispositivo fuerza la elección en consola
        config = None if a.dispositivo is not None else cargar_config()
        if config:
            entrada, fecha = config
            print(f"Configuración de audio del {fecha}: entrada «{entrada['nombre']}» canal {entrada['canal']}")
            avisar_api(entrada)
        else:
            entrada = elegir_entrada(a.dispositivo)
    print(f"Las sesiones se guardan en {CARPETA_SALIDA}")
    if a.prueba:
        datos = dict(datos_prueba(a.ninos), notas="recorrido de prueba")
    else:
        datos = pedir_datos(True if a.ninos else None)
    if entrada:
        datos["entrada"] = entrada  # dispositivo, canal y prueba de nivel quedan en sesion.json
    grabador = SinAudio() if a.sin_audio else Grabador(entrada)
    Sesion(datos, listas, calibracion, grabador, indicaciones, preguntas, imagenes, lectura,
           prueba=a.prueba).raiz.mainloop()


if __name__ == "__main__":
    sys.exit(main())
