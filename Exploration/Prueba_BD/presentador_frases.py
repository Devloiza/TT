"""Presentador de frases para la adquisición de voz de la base de datos (Obj. 3).

Hecho por Claude con la especificación del autor (2026-11-22). Es una utilidad de adquisición, no análisis del TT.
Diseño de la sesión: Metodologia/obj3_base_de_datos.md §4.1 (bloques b, c y f), §4.3 y §4.5.

Flujo:
  0. Audio: se toma de config_audio.json, que escribe configurar_audio.py una vez por máquina (micrófono con prueba
     de nivel y audífonos con tono de prueba). Si no existe o un dispositivo ya no aparece, se elige aquí en la
     consola: dispositivo, prueba de nivel de 3 s por canal, canal del micrófono y salida de los audífonos.
     La UMC202HD aparece como un par estéreo (IN 1-2): hay que elegir la entrada donde está el AT2020.
  1. Datos de la sesión (en la consola). El código se asigna solo (P01, P02…). Una sesión de prueba se guarda
     como P00, igual que las demás, pero no cuenta para el balance de listas. Se pide la edad exacta y el grupo se
     deduce de ella.
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
  5. Habla libre guiada (§4.3), cada bloque con una barra de tiempo:
       - imágenes (DURACION_IMAGENES s): de la carpeta CARPETA_IMAGENES, en orden balanceado entre participantes
         (las menos usadas primero, con semilla según el código). Con Espacio se pasa a la siguiente;
       - estilos guiados (DURACION_ESTILO s cada uno): fuerte, baja y susurro, con las primeras preguntas de
         preguntas.txt, fijas y en orden (una por estilo). Con Espacio se pasa a la siguiente pregunta;
       - plática (DURACION_PLATICA s): el resto de preguntas.txt en orden balanceado entre participantes (las menos
         usadas primero, con semilla según el código), con Espacio la siguiente. Con F, B, S y N el conductor pide
         otro estilo en medio de la plática.
     Las indicaciones y preguntas se muestran en pantalla y, si existe CARPETA_AUDIOS/<id>.wav, también suenan por
     la salida elegida (audífonos cerrados), para no grabar la voz del conductor. Cada reproducción queda en
     frases.csv como tipo «indicacion», para excluir lo que se filtre al micrófono.
  6. Guarda en SALIDAS/BD_voz/<código>_<fecha>/:
       audio.wav    48 kHz, 24 bits, una sola toma continua
       frases.csv   inicio y fin (s, en el reloj del audio) de cada frase, imagen o pregunta, con su estilo,
                    marca e interrupción
       sesion.json  datos de la sesión, entrada y salida de audio, ritmo medido, listas, imágenes y preguntas
                    mostradas, duraciones y eventos (pausas y cambios de estilo)

Teclas (solo el conductor; la persona no debe tener el teclado):
  Espacio  calibración: la persona terminó la frase. Imágenes y preguntas: la siguiente. Espera: continuar
  P        pausa de emergencia. Otra vez para reanudar; la frase interrumpida se muestra de nuevo completa.
           En habla libre, el bloque sigue con el tiempo que le quedaba
  R        repite la frase actual (o la que acaba de terminar) por un ruido externo fuerte; la toma anterior
           queda en frases.csv con repetida = 1
  M        marca la frase, imagen o pregunta actual como dudosa (ruido externo, palabra omitida…)
  F B S N  solo en la plática: pide voz fuerte, baja, susurro o normal
  Esc      termina la sesión antes y guarda lo grabado
  F11      pantalla completa

Uso:
  python Exploration/Prueba_BD/presentador_frases.py              sesión normal
  python Exploration/Prueba_BD/presentador_frases.py --listar     lista los dispositivos de entrada y de salida
  python Exploration/Prueba_BD/presentador_frases.py --prueba     recorrido corto y automático, sin participante
  Opciones: --dispositivo N y --salida N (índices de --listar), --sin-audio (no graba ni reproduce; para probar
  la pantalla)
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
ARCHIVO_LISTAS = CARPETA / "Lists_SHARVARD_MX.txt"
ARCHIVO_CALIBRACION = CARPETA / "calibracion.txt"
CARPETA_SALIDA = CARPETA.parents[1] / "SALIDAS" / "BD_voz"   # no se versiona (voces de personas)
ARCHIVO_ASIGNACIONES = CARPETA_SALIDA / "asignaciones.csv"
ARCHIVO_PREGUNTAS = CARPETA / "preguntas.txt"
CARPETA_IMAGENES = CARPETA / "image"             # no se versiona (Pexels); fuentes en fuentes_imagenes.csv
CARPETA_AUDIOS = CARPETA / "audios_preguntas"    # <id>.wav por indicación o pregunta; no se versiona
ARCHIVO_CONFIG = CARPETA / "config_audio.json"   # lo escribe configurar_audio.py; es de cada máquina, no se versiona

LISTAS_FIJAS = (15, 33, 3)
N_ALEATORIAS = 3
MARGEN = 1.25                 # tiempo de cada frase = sílabas × ritmo de calibración × MARGEN
SILENCIO_FRASES = 2.0         # s en blanco después de cada frase
SILENCIO_LISTAS = 5.0         # s en blanco entre listas
SILENCIO_REFERENCIA = 30.0    # s de silencio grabado al inicio (ruido de fondo de la sesión)
DURACION_IMAGENES = 180.0     # s del bloque de imágenes (las que alcancen)
DURACION_ESTILO = 75.0        # s de cada estilo guiado (fuerte, baja, susurro)
DURACION_PLATICA = 300.0      # s de plática al final
ESTILOS_GUIADOS = ("fuerte", "baja", "susurro")
TECLAS_ESTILO = {"f": "fuerte", "b": "baja", "s": "susurro", "n": "normal"}

FS = 48000                    # Hz
BLOQUE = 1024                 # muestras por bloque de grabación
TAM_TEXTO = 40                # tamaño de las frases en pantalla
TAM_AYUDA = 11                # línea de estado para el conductor
TAM_CONSIGNA = 22             # indicación arriba de la imagen o la pregunta
COLOR_CONSIGNA = "#1f5f8b"

ALTO_BARRA = 34               # barra de descanso (px)
COLOR_BARRA = "#7fb3d5"
COLOR_PROGRESO = "#82c99a"    # barra delgada: cuánto falta para el siguiente descanso
CODIGO_PRUEBA = "P00"         # sesiones de prueba: se guardan normal, pero no cuentan para el balance de listas
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
    faltan = {"imagen", "platica", "normal", *ESTILOS_GUIADOS} - indicaciones.keys()
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
    """Las primeras de preguntas.txt, una por estilo guiado, fijas y en orden; el resto, balanceado para la plática."""
    n = len(ESTILOS_GUIADOS)
    return list(preguntas[:n]) + balanceado(codigo, preguntas[n:], "preguntas", clave=lambda p: p[0])


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


def localizar(pa, guardado, validos):
    """Índice actual de un dispositivo guardado. Los índices cambian al conectar o desconectar aparatos, así que se
    busca por nombre y API; None si ya no está o dejó de aceptar el formato."""
    if guardado["dispositivo"] in validos and validos[guardado["dispositivo"]] == guardado["nombre"] \
            and api_de(pa, guardado["dispositivo"]) == guardado.get("api"):
        return guardado["dispositivo"]
    return next((i for i, nombre in validos.items()
                 if nombre == guardado["nombre"] and api_de(pa, i) == guardado.get("api")), None)


def cargar_config(ruta=ARCHIVO_CONFIG):
    """(entrada, salida, fecha) desde configurar_audio.py, con los índices actualizados; None si falta o no sirve."""
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
        salida = dict(config["salida"]) if config.get("salida") else None
        if salida is not None:
            j = localizar(pa, salida, dict(salidas_validas(pa)))
            if j is None:
                print(f"La salida guardada («{salida['nombre']}», {salida.get('api')}) no está conectada. "
                      "Conéctala o corre de nuevo configurar_audio.py.")
                return None
            salida["dispositivo"] = j
    finally:
        pa.terminate()
    return entrada, salida, config.get("fecha", "")


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
                print(f"  {i:>3}  {nombre}  ({canales} canal(es))")
            r = input("Índice del dispositivo: ").strip()
            dispositivo = int(r) if r.isdigit() and int(r) in {v[0] for v in validos} else None
            if dispositivo is None:
                continue
        _, nombre, canales = next(v for v in validos if v[0] == dispositivo)
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


# ----------------------------------------------------------------- reproducción (audífonos)
def salidas_validas(pa):
    """Salidas que aceptan FS en estéreo: [(índice, nombre)]."""
    import pyaudio
    validas = []
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info["maxOutputChannels"] < 2:
            continue
        try:
            pa.is_format_supported(FS, output_device=i, output_channels=2, output_format=pyaudio.paFloat32)
        except ValueError:
            continue
        validas.append((i, nombre_dispositivo(info)))
    return validas


def elegir_salida(salida=None):
    """En la consola: la salida de los audífonos (o ninguna) y un tono de prueba. Devuelve un dict o None."""
    import pyaudio
    pa = pyaudio.PyAudio()
    validas = salidas_validas(pa)
    nombres = dict(validas)
    while True:
        if salida is None:
            print(f"\nSalidas para los audífonos (aceptan {FS} Hz en estéreo):")
            for i, nombre in validas:
                print(f"  {i:>3}  {nombre}")
            r = input("Índice de la salida (Enter = sin audio: las indicaciones solo se muestran): ").strip()
            if not r:
                pa.terminate()
                return None
            salida = int(r) if r.isdigit() and int(r) in nombres else None
            if salida is None:
                continue
        input(f"Tono de prueba en «{nombres[salida]}»: ponte los audífonos y presiona Enter...")
        t = np.arange(int(FS * 1.0)) / FS
        tono = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        try:
            stream = pa.open(format=pyaudio.paFloat32, channels=2, rate=FS, output=True,
                             output_device_index=salida)
            stream.write(np.repeat(tono[:, None], 2, axis=1).tobytes())
            stream.stop_stream()
            stream.close()
        except OSError as e:
            print(f"No se pudo abrir: {e}")
            salida = None
            continue
        r = input("¿Se escuchó bien en los audífonos? [s = sí / n = otra salida / p = repetir]: ").strip().lower()
        if r == "s":
            api = api_de(pa, salida)
            pa.terminate()
            return {"dispositivo": salida, "nombre": nombres[salida], "api": api}
        if r == "n":
            salida = None


class Reproductor:
    """Reproduce indicaciones pregrabadas por la salida elegida sin detener la pantalla (stream con callback)."""

    PAUSA_ENTRE = 0.4  # s de silencio entre dos audios seguidos (indicación y pregunta)

    def __init__(self, salida):
        import pyaudio
        self.pa = pyaudio.PyAudio()
        self.salida = salida["dispositivo"]
        self.stream = None

    @staticmethod
    def cargar(ruta):
        """Audio en estéreo a FS (float32). Si el archivo viene a otra frecuencia, se remuestrea."""
        import soundfile
        from math import gcd
        from scipy.signal import resample_poly
        datos, fs = soundfile.read(ruta, dtype="float32", always_2d=True)
        datos = datos[:, :2] if datos.shape[1] >= 2 else np.repeat(datos, 2, axis=1)
        if fs != FS:
            g = gcd(FS, fs)
            datos = resample_poly(datos, FS // g, fs // g, axis=0).astype(np.float32)
        return datos

    def reproducir(self, rutas):
        """Reproduce los audios uno tras otro. Devuelve la duración total en s (0 si no hay ninguno)."""
        import pyaudio
        self.parar()
        partes = []
        for ruta in rutas:
            if partes:
                partes.append(np.zeros((int(self.PAUSA_ENTRE * FS), 2), np.float32))
            partes.append(self.cargar(ruta))
        if not partes:
            return 0.0
        datos = np.ascontiguousarray(np.concatenate(partes))
        pos = 0

        def entregar(_entrada, n, _info, _estado):
            nonlocal pos
            trozo = datos[pos:pos + n]
            pos += n
            if len(trozo) < n:
                trozo = np.vstack([trozo, np.zeros((n - len(trozo), 2), np.float32)])
                return trozo.tobytes(), pyaudio.paComplete
            return trozo.tobytes(), pyaudio.paContinue

        self.stream = self.pa.open(format=pyaudio.paFloat32, channels=2, rate=FS, output=True,
                                   output_device_index=self.salida, frames_per_buffer=BLOQUE,
                                   stream_callback=entregar)
        return len(datos) / FS

    def parar(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def cerrar(self):
        self.parar()
        self.pa.terminate()


# ----------------------------------------------------------------- sesión
class Sesion:
    def __init__(self, datos, listas, calibracion, grabador, indicaciones, preguntas, imagenes, reproductor=None,
                 prueba=False):
        self.datos, self.listas, self.calibracion, self.grab = datos, listas, calibracion, grabador
        self.indicaciones, self.preguntas, self.repro = indicaciones, preguntas, reproductor
        self.prueba = prueba
        escala = 0.15 if prueba else 1.0
        self.sil_ref, self.sil_frases, self.sil_listas = (SILENCIO_REFERENCIA * escala, SILENCIO_FRASES * escala,
                                                          SILENCIO_LISTAS * escala)
        escala_libre = 0.04 if prueba else 1.0
        self.dur_imagenes, self.dur_estilo, self.dur_platica = (DURACION_IMAGENES * escala_libre,
                                                                DURACION_ESTILO * escala_libre,
                                                                DURACION_PLATICA * escala_libre)
        self.orden, self.aleatorias = asignar_listas(datos["codigo"], sorted(listas))
        self.orden_imagenes = asignar_imagenes(datos["codigo"], imagenes)
        self.preguntas = asignar_preguntas(datos["codigo"], preguntas)
        if prueba:  # recorrido corto: 2 listas de 3 frases
            self.orden = self.orden[:2]
            self.calibracion = self.calibracion[:3]
        self.registro = []           # una fila por frase, imagen, pregunta o indicación
        self.eventos = []            # pausas, reanudaciones, cambios de estilo y fin anticipado
        self.duraciones_calib = []   # (segundos, sílabas)
        self.ritmo = None            # s por sílaba
        self.pasos, self.i, self.tarea, self.en_pausa = [], -1, None, False
        self.tras_frase = False      # True durante el silencio posterior a una frase ya leída
        self.fila_actual = None
        self.bloque = None           # habla libre en curso: tipo, estilo y segundos que le quedan
        self.k_imagen = 0
        self.k_libre = 0             # cuántas preguntas de la plática (las balanceadas) se han tomado
        self.foto = None             # referencia a la imagen mostrada (Tk la borra si no se guarda)

        self.raiz = tk.Tk()
        self.raiz.title("Presentador de frases")
        self.raiz.configure(bg="white")
        self.raiz.geometry("1200x700")
        # Barra de descanso arriba: se vacía conforme pasa el tiempo y dice "Descanso" (no es algo para leer)
        self.barra = tk.Canvas(self.raiz, height=ALTO_BARRA + 20, bg="white", highlightthickness=0)
        self.barra.pack(side="top", fill="x")
        self.barra_inicio = self.barra_total = self.barra_fin = None
        # Indicación del habla libre (estilo o tarea): solo aparece en esos bloques
        self.consigna = tk.Label(self.raiz, text="", font=("Arial", TAM_CONSIGNA, "bold"), bg="white",
                                 fg=COLOR_CONSIGNA, wraplength=1100, justify="center")
        self.texto = tk.Label(self.raiz, text="", font=("Arial", TAM_TEXTO), bg="white", fg="black",
                              wraplength=1100, justify="center")
        self.texto.pack(expand=True, fill="both")
        self.ayuda = tk.Label(self.raiz, text="", font=("Arial", TAM_AYUDA), bg="white", fg="gray60")
        self.ayuda.pack(side="bottom", fill="x")
        for tecla, accion in (("<space>", self.espacio), ("<p>", self.pausa), ("<P>", self.pausa),
                              ("<m>", self.marcar), ("<M>", self.marcar), ("<r>", self.repetir),
                              ("<R>", self.repetir), ("<Escape>", self.terminar),
                              ("<F11>", lambda e: self.raiz.attributes("-fullscreen",
                                                                       not self.raiz.attributes("-fullscreen")))):
            self.raiz.bind(tecla, accion)
        for letra, estilo in TECLAS_ESTILO.items():
            for t in (letra, letra.upper()):
                self.raiz.bind(f"<KeyPress-{t}>", lambda e, est=estilo: self.cambiar_estilo(est))
        self.raiz.protocol("WM_DELETE_WINDOW", lambda: self.terminar(None))

        self.pasos = [("espera", "Bienvenida.\nCuando estés listo, guardaremos silencio un momento."),
                      ("silencio_ref", None),
                      ("espera", "Antes de empezar: arriba verás una barra delgada que muestra\n"
                                 "cuánto falta para el siguiente descanso.\n\n"
                                 "Cuando aparezca una barra grande que dice «Descanso»,\n"
                                 "no hay nada que leer. Solo espera a que se vacíe."),
                      ("demo_descanso", None),
                      ("espera", "Ahora lee en voz alta cada frase, a tu ritmo normal.")]
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

    def estado(self, texto):
        self.ayuda.config(text=f"{texto}   |   Espacio · P pausa · R repetir · M marcar · Esc terminar · F11 pantalla completa")

    def mostrar_barra(self, segundos, al_terminar, etiqueta="Descanso", total=None):
        """Barra que se vacía en `segundos`. Con `total`, arranca ya gastada (para reanudar un bloque tras pausa)."""
        total = total or segundos
        self.barra_inicio, self.barra_total, self.barra_fin = time.monotonic() - (total - segundos), total, al_terminar
        self.barra_etiqueta = etiqueta
        self._animar_barra()

    def barra_restante(self):
        return max(0.0, self.barra_total - (time.monotonic() - self.barra_inicio))

    def _animar_barra(self):
        transcurrido = time.monotonic() - self.barra_inicio
        if transcurrido >= self.barra_total:
            self.ocultar_barra()
            return self.barra_fin()
        ancho, margen = max(self.barra.winfo_width(), 400), 60
        lleno = (ancho - 2 * margen) * (1 - transcurrido / self.barra_total)
        self.barra.delete("all")
        self.barra.create_rectangle(margen, 10, ancho - margen, 10 + ALTO_BARRA, outline="gray70", width=2)
        self.barra.create_rectangle(margen, 10, margen + lleno, 10 + ALTO_BARRA, fill=COLOR_BARRA, outline="")
        self.barra.create_text(ancho / 2, 10 + ALTO_BARRA / 2, font=("Arial", TAM_AYUDA + 5), fill="gray20",
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
        self.barra.create_text(ancho / 2, y + alto + 13, text=texto, font=("Arial", TAM_AYUDA + 1), fill="gray45")

    def _texto_restantes(self, faltan, ultima):
        if faltan == 0:
            return "¡Terminamos las frases!" if ultima else "Ahora viene un descanso"
        destino = "terminar" if ultima else "el descanso"
        return f"Falta 1 frase para {destino}" if faltan == 1 else f"Faltan {faltan} frases para {destino}"

    def limpiar_pantalla(self):
        """Quita la imagen, la consigna y el audio del habla libre (la frase se vuelve a escribir después)."""
        if self.repro is not None:
            self.repro.parar()
        self.foto = None
        self.texto.config(image="", text="", font=("Arial", TAM_TEXTO))
        self.consigna.pack_forget()

    def mostrar_consigna(self, texto):
        self.consigna.config(text=texto)
        self.consigna.pack(side="top", fill="x", pady=(4, 0), before=self.texto)

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
        self.texto.config(text=mensaje, fg="gray25")
        self.estado("Esperando al conductor (Espacio)")
        if self.prueba:
            self.programar(0.5, self.siguiente)

    def _silencio_ref(self, _):
        self.texto.config(text="Silencio, por favor.", fg="gray40")
        self.estado(f"Silencio de referencia ({self.sil_ref:.0f} s)")
        self.fila_actual = self._fila("silencio_referencia", "", "", "")
        self.mostrar_barra(self.sil_ref, self._cerrar_y_seguir, etiqueta="Silencio")

    def _calibracion(self, frase):
        self.texto.config(text=frase, fg="black")
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
        nuevos = [("espera", "Muy bien. Ahora seguirán más frases.\nLas frases cambiarán solas.")]
        for k, lista in enumerate(self.orden):
            if k:
                nuevos.append(("pausa_listas", None))
            nuevos += [("frase", (lista, num, frase)) for num, frase in enumerate(self.listas[lista], start=1)]
        # Habla libre guiada (§4.3): imágenes, estilos guiados y plática, cada bloque con su barra de tiempo
        if self.orden_imagenes:
            nuevos += [("espera", "Muy bien. Ahora vas a describir unas imágenes.\n"
                                  "Cuéntanos todo lo que veas, con tus propias palabras."),
                       ("imagenes", None)]
        nuevos.append(("espera", "Ahora vas a contestar unas preguntas,\ncambiando el volumen de tu voz."))
        nuevos += [("estilo", e) for e in ESTILOS_GUIADOS]
        nuevos += [("espera", "Por último, vamos a platicar un rato.\nNo hay respuestas correctas."),
                   ("platica", None),
                   ("espera", "¡Terminamos! Muchas gracias.")]
        self.pasos[self.i + 1:self.i + 1] = nuevos
        print(f"Ritmo de lectura: {self.ritmo:.3f} s/sílaba. Listas: {self.orden} (aleatorias: {self.aleatorias})")
        self.siguiente()

    def _frase(self, dato):
        lista, num, frase = dato
        duracion = silabas(frase) * self.ritmo * MARGEN
        self.texto.config(text=frase, fg="black")
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

    def _pausa_listas(self, _):
        self.texto.config(text="")
        self.estado(f"Descanso entre listas ({self.sil_listas:.0f} s)")
        self.mostrar_barra(self.sil_listas, self.siguiente)

    def _demo_descanso(self, _):
        self.texto.config(text="")
        self.estado("Demostración de la barra de descanso")
        self.mostrar_barra(self.sil_listas, self.siguiente)

    # ---- habla libre guiada: un bloque con tiempo fijo; Espacio cambia de imagen o de pregunta
    def _imagenes(self, _):
        self.bloque = {"tipo": "imagen", "estilo": "normal", "restante": self.dur_imagenes,
                       "total": self.dur_imagenes, "indicacion": "imagen"}
        self._correr_bloque(con_indicacion=True)

    def _estilo(self, estilo):
        # Cada estilo empieza con su pregunta fija (la primera para fuerte, la segunda para baja…)
        k = ESTILOS_GUIADOS.index(estilo) % len(self.preguntas)
        self.bloque = {"tipo": "estilos", "estilo": estilo, "restante": self.dur_estilo, "total": self.dur_estilo,
                       "indicacion": estilo, "k": k}
        self._correr_bloque(con_indicacion=True)

    def _platica(self, _):
        self.bloque = {"tipo": "platica", "estilo": "normal", "restante": self.dur_platica,
                       "total": self.dur_platica, "indicacion": "platica", "k": self._tomar_libre()}
        self._correr_bloque(con_indicacion=True)

    def _tomar_libre(self):
        """Índice de la siguiente pregunta balanceada (las que no son de los estilos guiados). Si se acaban,
        vuelven a empezar."""
        fijas = len(ESTILOS_GUIADOS) if len(self.preguntas) > len(ESTILOS_GUIADOS) else 0
        k = fijas + self.k_libre % (len(self.preguntas) - fijas)
        self.k_libre += 1
        return k

    def _correr_bloque(self, con_indicacion):
        """Muestra el elemento actual y arranca (o retoma) la barra con el tiempo que le queda al bloque."""
        b = self._mostrar_elemento(con_indicacion)
        self.mostrar_barra(b["restante"], self._fin_bloque, etiqueta="Tiempo", total=b["total"])
        if self.prueba:
            self._auto_espacio(self.i)

    def _auto_espacio(self, i):
        """--prueba: pasa de imagen o de pregunta sola; en la plática prueba también un cambio de estilo."""
        def paso():
            if self.i != i or self.en_pausa or self.bloque is None:
                return
            if self.bloque["tipo"] == "platica" and self.bloque["estilo"] == "normal":
                self.cambiar_estilo("baja")
            else:
                self.espacio(None)
            self.raiz.after(2500, paso)
        self.raiz.after(2500, paso)

    def _mostrar_elemento(self, con_indicacion):
        """Imagen o pregunta actual en pantalla, fila nueva en el registro y su audio por los audífonos."""
        b = self.bloque
        self.limpiar_pantalla()
        audios = [b["indicacion"]] if con_indicacion else []
        if b["tipo"] == "imagen":
            nombre = self.orden_imagenes[self.k_imagen % len(self.orden_imagenes)]
            self.mostrar_consigna(self.indicaciones["imagen"])
            self._dibujar_imagen(nombre)
            self.fila_actual = self._fila("imagen", "", self.k_imagen + 1, nombre, estilo=b["estilo"])
            self.estado(f"Imagen {self.k_imagen + 1}: {nombre}. Espacio = siguiente imagen")
        else:
            clave, pregunta = self.preguntas[b["k"]]
            consigna = self.indicaciones["platica" if b["tipo"] == "platica" and b["estilo"] == "normal"
                                         else b["estilo"]]
            self.mostrar_consigna(consigna)
            self.texto.config(text=pregunta, fg="black")
            self.fila_actual = self._fila(b["tipo"], "", clave, pregunta, estilo=b["estilo"])
            audios.append(clave)
            extra = " · F B S N = estilo" if b["tipo"] == "platica" else ""
            self.estado(f"{b['tipo'].capitalize()} ({b['estilo']}), pregunta {clave}. Espacio = siguiente{extra}")
        self._reproducir(audios)
        return b

    def _dibujar_imagen(self, nombre):
        from PIL import Image, ImageOps, ImageTk
        self.raiz.update_idletasks()
        ancho = max(self.texto.winfo_width(), 600) - 40
        alto = max(self.texto.winfo_height(), 400) - 20
        with Image.open(CARPETA_IMAGENES / nombre) as im:
            im.draft("RGB", (max(ancho, alto),) * 2)  # decodifica el JPEG ya reducido: mucho más rápido
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((ancho, alto))
        self.foto = ImageTk.PhotoImage(im)
        self.texto.config(image=self.foto, text="")

    def _reproducir(self, claves):
        """Reproduce los audios que existan y los anota como «indicacion» (para excluir lo que se filtre al mic)."""
        if self.repro is None:
            return
        rutas = [CARPETA_AUDIOS / f"{c}.wav" for c in claves if (CARPETA_AUDIOS / f"{c}.wav").exists()]
        if not rutas:
            return
        inicio = self.grab.tiempo()
        try:
            duracion = self.repro.reproducir(rutas)
        except Exception as e:  # un audio dañado no debe tirar la sesión: queda solo el texto
            print(f"No se pudo reproducir {[r.name for r in rutas]}: {e}")
            return
        fila = self._fila("indicacion", "", "", " ".join(r.stem for r in rutas), estilo="")
        fila["inicio_s"], fila["fin_s"] = round(inicio, 3), round(inicio + duracion, 3)
        self.registro.append(fila)

    def _siguiente_elemento(self):
        self._cerrar_fila()
        if self.bloque["tipo"] == "imagen":
            self.k_imagen += 1
        else:  # en los estilos guiados, la pregunta extra también sale de las balanceadas
            self.bloque["k"] = self._tomar_libre()
        self._mostrar_elemento(con_indicacion=False)

    def cambiar_estilo(self, estilo):
        """Solo en la plática: el conductor pide otro estilo; la pregunta sigue en pantalla y la barra no se detiene."""
        b = self.bloque
        if self.en_pausa or b is None or b["tipo"] != "platica" or b["estilo"] == estilo:
            return
        self._cerrar_fila()
        b["estilo"], b["indicacion"] = estilo, estilo
        self.eventos.append({"evento": "estilo", "estilo": estilo, "t_s": round(self.grab.tiempo(), 3)})
        clave, pregunta = self.preguntas[b["k"]]
        self.limpiar_pantalla()
        self.mostrar_consigna(self.indicaciones[estilo])
        self.texto.config(text=pregunta, fg="black")
        self.fila_actual = self._fila("platica", "", clave, pregunta, estilo=estilo)
        self.estado(f"Plática ({estilo}), pregunta {clave}. Espacio = siguiente · F B S N = estilo")
        self._reproducir([estilo])

    def _fin_bloque(self):
        self._cerrar_fila()
        self.siguiente()

    # ---- registro
    def _fila(self, tipo, lista, num, texto, estilo="normal"):
        """Una fila de frases.csv. En habla libre, «frase» es el número de imagen o el id de la pregunta."""
        lectura = tipo in ("frase", "calibracion")
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
    def espacio(self, _evento):
        if self.en_pausa or self.i >= len(self.pasos):
            return
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

    def pausa(self, _evento):
        if self.i >= len(self.pasos):
            return
        if not self.en_pausa:
            self.en_pausa = True
            if self.bloque is not None:  # habla libre: al reanudar sigue con el tiempo que le quedaba
                self.bloque["restante"] = self.barra_restante()
            self.cancelar()
            self.ocultar_barra()
            self.limpiar_pantalla()
            if self.fila_actual is not None:
                self._cerrar_fila(interrumpida=True)
            self.eventos.append({"evento": "pausa", "t_s": round(self.grab.tiempo(), 3)})
            self.texto.config(text="Pausa", fg="gray50")
            self.estado("PAUSA: P para reanudar (la frase interrumpida se repite completa)")
        else:
            self.en_pausa = False
            self.eventos.append({"evento": "reanudacion", "t_s": round(self.grab.tiempo(), 3)})
            if self.bloque is not None:  # misma imagen o pregunta; su audio se repite, sin la indicación
                self._correr_bloque(con_indicacion=False)
            elif self.tras_frase:  # la frase ya se había leído completa: sigue con la próxima
                self.siguiente()
            else:
                tipo, dato = self.pasos[self.i]
                getattr(self, f"_{tipo}")(dato)  # repite el paso actual desde el inicio

    def repetir(self, _evento):
        """Repite la frase actual (o la que acaba de terminar) por un ruido externo fuerte. La toma anterior queda
        en frases.csv con repetida = 1, para descartarla al etiquetar."""
        if self.en_pausa or self.i >= len(self.pasos):
            return
        tipo, dato = self.pasos[self.i]
        if tipo not in ("frase", "calibracion"):
            return
        self.cancelar()
        if self.fila_actual is not None:
            self._cerrar_fila(repetida=True)
        elif self.tras_frase and self.registro:
            self.registro[-1]["repetida"] = 1
        self.tras_frase = False
        self.eventos.append({"evento": "repeticion", "t_s": round(self.grab.tiempo(), 3),
                             "lista": dato[0] if tipo == "frase" else "C",
                             "frase": dato[1] if tipo == "frase" else ""})
        self.estado("Repitiendo la frase")
        getattr(self, f"_{tipo}")(dato)

    def marcar(self, _evento):
        if self.fila_actual is not None:
            self.fila_actual["marcada"] = 1
        elif self.registro:  # durante el silencio posterior: marca la frase que acaba de terminar
            self.registro[-1]["marcada"] = 1
        self.estado("Frase marcada")

    def terminar(self, _evento):
        self.eventos.append({"evento": "fin_anticipado", "t_s": round(self.grab.tiempo(), 3)})
        self._cerrar_fila(interrumpida=True)
        self.finalizar()

    # ---- cierre
    def finalizar(self):
        self.cancelar()
        if self.repro is not None:
            self.repro.cerrar()
        audio = self.grab.detener()
        carpeta = CARPETA_SALIDA / f"{self.datos['codigo']}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        carpeta.mkdir(parents=True, exist_ok=True)
        if audio is not None:
            import soundfile
            soundfile.write(carpeta / "audio.wav", audio, FS, subtype="PCM_24")
        self.registro.sort(key=lambda r: r["inicio_s"])  # las indicaciones se anotan antes de que cierre su fila
        with open(carpeta / "frases.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["tipo", "lista", "frase", "texto", "silabas", "estilo", "inicio_s", "fin_s",
                                   "marcada", "interrumpida", "repetida"])
            w.writeheader()
            w.writerows(self.registro)
        completas = [l for l in self.orden  # cada frase de la lista con al menos una toma válida
                     if len({r["frase"] for r in self.registro if r["lista"] == l and not r["interrumpida"]
                             and not r["repetida"]}) == len(self.listas[l])]
        mostradas = list(dict.fromkeys(r["texto"] for r in self.registro if r["tipo"] == "imagen"))
        hechas = list(dict.fromkeys(r["frase"] for r in self.registro if r["tipo"] in ("estilos", "platica")))
        sesion = dict(self.datos, fecha=datetime.datetime.now().isoformat(timespec="seconds"), prueba=self.prueba,
                      ritmo_s_por_silaba=self.ritmo, margen=MARGEN, silencio_frases_s=self.sil_frases,
                      silencio_listas_s=self.sil_listas, silencio_referencia_s=self.sil_ref,
                      listas_orden=self.orden, listas_fijas=list(LISTAS_FIJAS), listas_aleatorias=self.aleatorias,
                      listas_completas=completas, imagenes_mostradas=mostradas, preguntas_mostradas=hechas,
                      duracion_imagenes_s=self.dur_imagenes, duracion_estilo_s=self.dur_estilo,
                      duracion_platica_s=self.dur_platica, eventos=self.eventos, fs=FS, bits=24,
                      archivo_listas=ARCHIVO_LISTAS.name, archivo_calibracion=ARCHIVO_CALIBRACION.name,
                      archivo_preguntas=ARCHIVO_PREGUNTAS.name)
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


def pedir_datos():
    def opcion(pregunta, opciones):
        while True:
            r = input(f"{pregunta} {list(opciones)}: ").strip().lower()
            if r in opciones:
                return r
    prueba = opcion(f"¿Es una sesión de prueba? (se guarda como {CODIGO_PRUEBA})", ("s", "n")) == "s"
    codigo = CODIGO_PRUEBA if prueba else siguiente_codigo()
    print(f"Código asignado: {codigo}")
    edad = None
    while edad is None:
        r = input("Edad (años): ").strip()
        edad = int(r) if r.isdigit() and 3 <= int(r) <= 110 else None
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
    p.add_argument("--salida", type=int, default=None,
                   help="índice de la salida de los audífonos (si no se da, se elige en la consola)")
    p.add_argument("--prueba", action="store_true", help="recorrido corto y automático")
    p.add_argument("--sin-audio", action="store_true", help="no graba ni reproduce (solo prueba la pantalla)")
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
                print(f"{i:>3} [{marca}] {nombre_dispositivo(d)}  ({int(d['defaultSampleRate'])} Hz)")
        print(f"[OK] = acepta {FS} Hz y 24 bits")
        print("\nSalidas:")
        validas = {v[0] for v in salidas_validas(pa)}
        for i in range(pa.get_device_count()):
            d = pa.get_device_info_by_index(i)
            if d["maxOutputChannels"] > 0:
                marca = "OK" if i in validas else "--"
                print(f"{i:>3} [{marca}] {nombre_dispositivo(d)}  ({int(d['defaultSampleRate'])} Hz)")
        print(f"[OK] = acepta {FS} Hz en estéreo")
        pa.terminate()
        return
    listas, calibracion = leer_listas(), leer_calibracion()
    indicaciones, preguntas = leer_preguntas()
    imagenes = leer_imagenes()
    if not imagenes:
        print(f"AVISO: no hay imágenes en {CARPETA_IMAGENES}; se omite el bloque de imágenes.")
    sin_audio = [c for c in [*indicaciones, *(c for c, _ in preguntas)] if not (CARPETA_AUDIOS / f"{c}.wav").exists()]
    if sin_audio:
        print(f"AVISO: sin audio en {CARPETA_AUDIOS.name}/ (solo se mostrará el texto): {', '.join(sin_audio)}")
    entrada = salida = None
    if not a.sin_audio:
        # Con la configuración guardada no se pregunta nada; --dispositivo o --salida fuerzan la elección en consola
        config = None if a.dispositivo is not None or a.salida is not None else cargar_config()
        if config:
            entrada, salida, fecha = config
            print(f"Configuración de audio del {fecha}: entrada «{entrada['nombre']}» canal {entrada['canal']}, "
                  f"audífonos: {'«' + salida['nombre'] + '»' if salida else 'sin audio'}")
        else:
            entrada = elegir_entrada(a.dispositivo)
            salida = elegir_salida(a.salida)
    datos = ({"codigo": CODIGO_PRUEBA, "edad": 25, "grupo_edad": "adulto joven", "sexo": "h", "lugar": "cubículo", "ganancia": "",
              "sonometro_fondo_dba": "", "conductor": "prueba", "notas": "recorrido de prueba"}
             if a.prueba else pedir_datos())
    if entrada:
        datos["entrada"] = entrada  # dispositivo, canal y prueba de nivel quedan en sesion.json
    datos["salida_audifonos"] = salida
    datos["audios_faltantes"] = sin_audio
    grabador = SinAudio() if a.sin_audio else Grabador(entrada)
    reproductor = Reproductor(salida) if salida else None
    Sesion(datos, listas, calibracion, grabador, indicaciones, preguntas, imagenes, reproductor,
           prueba=a.prueba).raiz.mainloop()


if __name__ == "__main__":
    sys.exit(main())
