"""Presentador de frases para la adquisición de voz de la base de datos (Obj. 3).

Hecho por Claude con la especificación del autor (2026-11-22). Es una utilidad de adquisición, no análisis del TT.
Diseño de la sesión: Metodologia/obj3_base_de_datos.md §4.1 (bloques b y c).

Flujo:
  0. Entrada de audio (en la consola): dispositivo, prueba de nivel de 3 s por canal y canal del micrófono.
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
  5. Guarda en SALIDAS/BD_voz/<código>_<fecha>/:
       audio.wav    48 kHz, 24 bits, una sola toma continua
       frases.csv   inicio y fin (s, en el reloj del audio) de cada frase, con marca e interrupción
       sesion.json  datos de la sesión, ritmo medido, listas y eventos de pausa

Teclas (solo el conductor; la persona no debe tener el teclado):
  Espacio  calibración: la persona terminó la frase. En pantallas de espera: continuar
  P        pausa de emergencia. Otra vez para reanudar; la frase interrumpida se muestra de nuevo completa
  R        repite la frase actual (o la que acaba de terminar) por un ruido externo fuerte; la toma anterior
           queda en frases.csv con repetida = 1
  M        marca la frase actual como dudosa (ruido externo, palabra omitida…), sin detener nada
  Esc      termina la sesión antes y guarda lo grabado
  F11      pantalla completa

Uso:
  python Exploration/Prueba_BD/presentador_frases.py              sesión normal
  python Exploration/Prueba_BD/presentador_frases.py --listar     lista los dispositivos de entrada
  python Exploration/Prueba_BD/presentador_frases.py --prueba     recorrido corto y automático, sin participante
  Opciones: --dispositivo N (índice de --listar) y --sin-audio (no graba; para probar la pantalla)
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

LISTAS_FIJAS = (15, 33, 3)
N_ALEATORIAS = 3
MARGEN = 1.25                 # tiempo de cada frase = sílabas × ritmo de calibración × MARGEN
SILENCIO_FRASES = 2.0         # s en blanco después de cada frase
SILENCIO_LISTAS = 5.0         # s en blanco entre listas
SILENCIO_REFERENCIA = 30.0    # s de silencio grabado al inicio (ruido de fondo de la sesión)

FS = 48000                    # Hz
BLOQUE = 1024                 # muestras por bloque de grabación
TAM_TEXTO = 40                # tamaño de las frases en pantalla
TAM_AYUDA = 11                # línea de estado para el conductor

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
            pa.terminate()
            return {"dispositivo": dispositivo, "nombre": nombre, "canales": canales, "canal": canal,
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
    def __init__(self, datos, listas, calibracion, grabador, prueba=False):
        self.datos, self.listas, self.calibracion, self.grab = datos, listas, calibracion, grabador
        self.prueba = prueba
        escala = 0.15 if prueba else 1.0
        self.sil_ref, self.sil_frases, self.sil_listas = (SILENCIO_REFERENCIA * escala, SILENCIO_FRASES * escala,
                                                          SILENCIO_LISTAS * escala)
        self.orden, self.aleatorias = asignar_listas(datos["codigo"], sorted(listas))
        if prueba:  # recorrido corto: 2 listas de 3 frases
            self.orden = self.orden[:2]
            self.calibracion = self.calibracion[:3]
        self.registro = []           # una fila por frase mostrada
        self.eventos = []            # pausas, reanudaciones y fin anticipado
        self.duraciones_calib = []   # (segundos, sílabas)
        self.ritmo = None            # s por sílaba
        self.pasos, self.i, self.tarea, self.en_pausa = [], -1, None, False
        self.tras_frase = False      # True durante el silencio posterior a una frase ya leída
        self.fila_actual = None

        self.raiz = tk.Tk()
        self.raiz.title("Presentador de frases")
        self.raiz.configure(bg="white")
        self.raiz.geometry("1200x700")
        # Barra de descanso arriba: se vacía conforme pasa el tiempo y dice "Descanso" (no es algo para leer)
        self.barra = tk.Canvas(self.raiz, height=ALTO_BARRA + 20, bg="white", highlightthickness=0)
        self.barra.pack(side="top", fill="x")
        self.barra_inicio = self.barra_total = self.barra_fin = None
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

    def mostrar_barra(self, segundos, al_terminar, etiqueta="Descanso"):
        self.barra_inicio, self.barra_total, self.barra_fin = time.monotonic(), segundos, al_terminar
        self.barra_etiqueta = etiqueta
        self._animar_barra()

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
                               text=f"{self.barra_etiqueta} · {self.barra_total - transcurrido:.0f} s")
        self.tarea = self.raiz.after(50, self._animar_barra)

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
            return "¡Terminamos!" if ultima else "Ahora viene un descanso"
        destino = "terminar" if ultima else "el descanso"
        return f"Falta 1 frase para {destino}" if faltan == 1 else f"Faltan {faltan} frases para {destino}"

    def siguiente(self):
        self.cancelar()
        self.ocultar_barra()
        self.tras_frase = False
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
        nuevos.append(("espera", "¡Terminamos! Muchas gracias."))
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

    # ---- registro
    def _fila(self, tipo, lista, num, texto):
        return {"tipo": tipo, "lista": lista, "frase": num, "texto": texto, "silabas": silabas(texto) if texto else "",
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
            self.cancelar()
            self.ocultar_barra()
            if self.fila_actual is not None:
                self._cerrar_fila(interrumpida=True)
            self.eventos.append({"evento": "pausa", "t_s": round(self.grab.tiempo(), 3)})
            self.texto.config(text="Pausa", fg="gray50")
            self.estado("PAUSA: P para reanudar (la frase interrumpida se repite completa)")
        else:
            self.en_pausa = False
            self.eventos.append({"evento": "reanudacion", "t_s": round(self.grab.tiempo(), 3)})
            if self.tras_frase:  # la frase ya se había leído completa: sigue con la próxima
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
        audio = self.grab.detener()
        carpeta = CARPETA_SALIDA / f"{self.datos['codigo']}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
        carpeta.mkdir(parents=True, exist_ok=True)
        if audio is not None:
            import soundfile
            soundfile.write(carpeta / "audio.wav", audio, FS, subtype="PCM_24")
        with open(carpeta / "frases.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["tipo", "lista", "frase", "texto", "silabas", "inicio_s", "fin_s", "marcada",
                                   "interrumpida", "repetida"])
            w.writeheader()
            w.writerows(self.registro)
        completas = [l for l in self.orden  # cada frase de la lista con al menos una toma válida
                     if len({r["frase"] for r in self.registro if r["lista"] == l and not r["interrumpida"]
                             and not r["repetida"]}) == len(self.listas[l])]
        sesion = dict(self.datos, fecha=datetime.datetime.now().isoformat(timespec="seconds"), prueba=self.prueba,
                      ritmo_s_por_silaba=self.ritmo, margen=MARGEN, silencio_frases_s=self.sil_frases,
                      silencio_listas_s=self.sil_listas, silencio_referencia_s=self.sil_ref,
                      listas_orden=self.orden, listas_fijas=list(LISTAS_FIJAS), listas_aleatorias=self.aleatorias,
                      listas_completas=completas, eventos=self.eventos, fs=FS, bits=24,
                      archivo_listas=ARCHIVO_LISTAS.name, archivo_calibracion=ARCHIVO_CALIBRACION.name)
        (carpeta / "sesion.json").write_text(json.dumps(sesion, ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.prueba and self.datos["codigo"] != CODIGO_PRUEBA:  # las pruebas no cuentan para el balance
            nuevo = not ARCHIVO_ASIGNACIONES.exists()
            with open(ARCHIVO_ASIGNACIONES, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if nuevo:
                    w.writerow(["codigo", "fecha", "listas_completas"])
                w.writerow([self.datos["codigo"], sesion["fecha"], " ".join(map(str, completas))])
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
    p.add_argument("--prueba", action="store_true", help="recorrido corto y automático")
    p.add_argument("--sin-audio", action="store_true", help="no graba (solo prueba la pantalla)")
    a = p.parse_args()
    if a.listar:
        import pyaudio
        pa = pyaudio.PyAudio()
        validos = {v[0] for v in dispositivos_validos(pa)}
        for i in range(pa.get_device_count()):
            d = pa.get_device_info_by_index(i)
            if d["maxInputChannels"] > 0:
                marca = "OK" if i in validos else "--"
                print(f"{i:>3} [{marca}] {nombre_dispositivo(d)}  ({int(d['defaultSampleRate'])} Hz)")
        print(f"[OK] = acepta {FS} Hz y 24 bits")
        pa.terminate()
        return
    listas, calibracion = leer_listas(), leer_calibracion()
    entrada = None
    if not a.sin_audio:
        entrada = elegir_entrada(a.dispositivo)
    datos = ({"codigo": CODIGO_PRUEBA, "edad": 25, "grupo_edad": "adulto joven", "sexo": "h", "lugar": "cubículo", "ganancia": "",
              "sonometro_fondo_dba": "", "conductor": "prueba", "notas": "recorrido de prueba"}
             if a.prueba else pedir_datos())
    if entrada:
        datos["entrada"] = entrada  # dispositivo, canal y prueba de nivel quedan en sesion.json
    grabador = SinAudio() if a.sin_audio else Grabador(entrada)
    Sesion(datos, listas, calibracion, grabador, prueba=a.prueba).raiz.mainloop()


if __name__ == "__main__":
    sys.exit(main())
