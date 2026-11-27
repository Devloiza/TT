"""Espectro del ruido del lugar, para no depender solo del sonómetro (Obj. 3).

Hecho por Claude con la especificación del autor (2026-11-24). Es una utilidad de diagnóstico de la adquisición; sus
cifras no son resultados del TT.

Tres modos:
  1. Medir ahora: graba por la misma entrada que presentador_frases.py (config_audio.json) y muestra el espectro, para
     revisar el lugar antes de una sesión. Guarda audio.wav y espectro.png en CARPETA_SALIDA/ruido_<fecha>/.
  2. Abrir una sesión (--sesion): compara el silencio de referencia con cada estilo de voz. Guarda espectro.png en la
     carpeta de la sesión.
  3. En vivo (--vivo): monitoreo en tiempo real. Arriba, la curva del espectro (último segundo y mediana de los últimos
     30 s); abajo, el mapa de calor de esos 30 s, con lo más reciente arriba. Comparten el eje de frecuencia.
     Muestra el nivel por banda y el pico, y avisa si satura o si se perdió audio. No graba ni guarda nada.
     Teclas: 1, 2 y 3 = vista; Espacio = pausa; A = reajustar la escala. Cerrar la ventana para salir.
     Vistas (VISTAS): 1 completa, logarítmica; 2 de 0 a 1000 Hz y 3 de 0 a 4000 Hz, lineales: en ellas los armónicos
     quedan separados por la misma distancia. La 2 lleva una marca cada 60 Hz.

Qué muestra:
  - Densidad espectral del ruido (Welch, ventana de Hann, resolución de ~1.5 Hz) de 20 Hz a 24 kHz. La mediana es el
    ruido constante; si la media queda muy por arriba, hubo ruidos momentáneos (golpes, pasos, voces). En tonos puros
    la mediana queda ~1.5 dB arriba de la media, por su corrección estadística.
  - Líneas en 60 Hz y sus armónicos (interferencia eléctrica) y los picos que sobresalen de su entorno.
  - Nivel por banda. «80-8000» es lo que queda después del pasa-altas y de bajar a 16 kHz (metodología §4.4).
  - Con --sesion, la diferencia (voz + ruido) - ruido por tercio de octava. La voz solo cuenta las tramas activas: las
    que superan el percentil 95 del silencio entre 100 y 8000 Hz, y se toma su mediana. 3 dB de diferencia es voz y
    ruido iguales.

Unidades: dBFS, donde 0 dBFS es un valor eficaz de 1 (un seno a fondo de escala da -3). Dependen de la ganancia de la
interfaz: solo se comparan mediciones con la misma ganancia. No es dB SPL: no hay calibración absoluta. En vivo la
resolución es de ~3 Hz, así que los tonos puros se ven unos 3 dB más bajos que en los otros modos.

Uso:
  python Exploration/Prueba_BD/espectro_ruido.py                     mide ahora (30 s)
  python Exploration/Prueba_BD/espectro_ruido.py --vivo              monitoreo en tiempo real
  python Exploration/Prueba_BD/espectro_ruido.py --sesion ultima     la última sesión guardada
  python Exploration/Prueba_BD/espectro_ruido.py --sesion P00_20261123_123909
  Opciones: --segundos N, --dispositivo N (de presentador_frases.py --listar), --sin-ventana (solo guarda la figura)
"""
import argparse
import csv
import datetime
import sys
import time
from collections import deque
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import soundfile
from matplotlib.animation import FuncAnimation
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from scipy.ndimage import median_filter
from scipy.signal import find_peaks, spectrogram, welch

import presentador_frases as pf

SEGUNDOS = 30.0
RECORTE = 1.0                  # s que se descartan en cada extremo del silencio (tecla, movimiento)
NPERSEG = 2 ** 15              # Welch del ruido: 48000 / 32768 = 1.5 Hz
NTRAMA = 4096                  # tramas de la comparación con la voz (~85 ms)
MIN_FILA = 2.0                 # s: se ignoran filas más cortas (cambios rápidos de estilo)
N_PICOS, SALIENTE_DB = 8, 6.0  # picos que se marcan: los que sobresalen al menos SALIENTE_DB de su entorno
BANDAS = ((20, 80), (80, 500), (500, 2000), (2000, 8000), (8000, 24000), (80, 8000))
TERCIOS = 1000 * 2.0 ** (np.arange(-12, 14) / 3)   # centros de 1/3 de octava, 63 Hz a 20 kHz

# Modo en vivo
NVIVO, SALTO = 2 ** 14, 2 ** 11   # ventana de 341 ms (2.9 Hz), una trama nueva cada 43 ms
REFRESCO_MS = 10                  # espera entre cuadros; matplotlib la suma al tiempo de dibujo (~45 ms)
PROMEDIO_VIVO = 1.0               # s que promedia la curva actual
HISTORIAL = 30.0                  # s del mapa de calor y de la mediana (ruido constante)
COLUMNAS = 900                    # columnas del mapa y de las curvas
SATURA_DBFS = -1.0                # pico a partir del cual avisa

ESTILOS = ("normal", "fuerte", "baja", "susurro")   # baja y susurro: solo en sesiones anteriores al 2026-11-24
COLOR = {"normal": "#2a78d6", "fuerte": "#eb6834", "baja": "#1baf7a", "susurro": "#4a3aa7"}
TRAZO = {"normal": "-", "fuerte": "--", "baja": "-.", "susurro": ":"}
TINTA, TINTA2, TENUE = "#0b0b0b", "#52514e", "#d9d8d3"
CALOR = "magma"                # más claro = más nivel (elección del autor)
MARCAS_HZ = (20, 60, 100, 200, 500, 1000, 2000, 5000, 10000, 20000)
# tecla: (nombre, Hz inicial, Hz final, logarítmica, marcas del eje)
VISTAS = {"1": ("completa", 20, 24000, True, MARCAS_HZ),
          "2": ("red y armónicos", 0, 1000, False, tuple(range(0, 1000, 60))),
          "3": ("armónicos de la voz", 0, 4000, False, tuple(range(0, 4001, 500)))}

def db(p):
    return 10 * np.log10(np.maximum(p, 1e-20))


# ----------------------------------------------------------------- cálculo
def densidad(x, fs):
    """(f, mediana, media) de la densidad espectral de potencia (Welch)."""
    n = min(NPERSEG, len(x))
    f, mediana = welch(x, fs, "hann", n, average="median")
    return f, mediana, welch(x, fs, "hann", n, average="mean")[1]


def nivel(f, psd, f1, f2):
    """Nivel en dBFS de la banda [f1, f2)."""
    m = (f >= f1) & (f < f2)
    return db(psd[m].sum() * (f[1] - f[0]))


def picos(f, psd):
    """[(frecuencia, dB sobre su entorno)] de los picos más salientes; el entorno es la mediana de ~60 Hz."""
    d = db(psd)
    exceso = d - median_filter(d, size=41)
    exceso[(f < 20) | (f > 20000)] = 0
    i, _ = find_peaks(exceso, height=SALIENTE_DB, distance=5)
    i = i[np.argsort(exceso[i])[::-1][:N_PICOS]]
    return sorted((f[k], exceso[k]) for k in i)


def armonico_de_60(frec, ancho):
    k = round(frec / 60)
    return k if k >= 1 and abs(frec - 60 * k) <= ancho else None


def matriz_bandas(f, limites):
    """Matriz (bandas, frecuencias) que suma la potencia de cada banda."""
    return np.array([(f >= a) & (f < b) for a, b in limites], dtype=float) * (f[1] - f[0])


def tramas(x, fs, limites):
    """Potencia por trama y banda: (tramas, bandas)."""
    f, _, s = spectrogram(x, fs, "hann", NTRAMA, NTRAMA // 2, detrend="constant")
    return (matriz_bandas(f, limites) @ s).T


# ----------------------------------------------------------------- consola
def informe_ruido(f, mediana, media, fs):
    print("\nRuido (dBFS por banda)      mediana    media   media - mediana")
    for a, b in BANDAS:
        m1, m2 = nivel(f, mediana, a, b), nivel(f, media, a, b)
        nota = "   <- tras el pasa-altas y 16 kHz" if (a, b) == (80, 8000) else ""
        print(f"  {a:>6}-{b:<6} Hz          {m1:8.1f} {m2:8.1f} {m2 - m1:10.1f}{nota}")
    total = mediana[f >= 20].sum()
    print(f"  Energía debajo de 80 Hz: {100 * mediana[(f >= 20) & (f < 80)].sum() / total:.0f} % del ruido constante")
    lista = picos(f, mediana)
    print("Picos (dB sobre su entorno):" if lista else "Sin picos que sobresalgan de su entorno.")
    for frec, ex in lista:
        k = armonico_de_60(frec, fs / NPERSEG * 0.75)  # menos de un bin: la red es muy estable
        origen = "" if k is None else ("  <- 60 Hz (red eléctrica)" if k == 1 else f"  <- armónico {k} de 60 Hz")
        print(f"  {frec:8.1f} Hz  +{ex:4.1f} dB{origen}")
    return lista


# ----------------------------------------------------------------- gráficas
def etiqueta_hz(m):
    return f"{m / 1000:g}k" if m >= 1000 else str(m)


def ejes(ax, ylabel):
    ax.set_xscale("log")
    ax.set_xlim(20, 24000)
    ax.set_xticks(MARCAS_HZ, [etiqueta_hz(m) for m in MARCAS_HZ])
    ax.minorticks_off()
    ax.grid(True, color=TENUE, linewidth=0.6)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.set_ylabel(ylabel, color=TINTA2)
    ax.tick_params(colors=TINTA2)


def graficar_ruido(ax, f, mediana, media, lista):
    m = f >= 20
    ejes(ax, "dBFS / Hz")
    for k in range(1, 11):
        ax.axvline(60 * k, color="#e34948", linewidth=0.8, alpha=0.35,
                   label="60 Hz y armónicos" if k == 1 else None)
    ax.axvspan(20, 80, color=TENUE, alpha=0.45, linewidth=0, label="Debajo de 80 Hz (pasa-altas)")
    ax.plot(f[m], db(media[m]), color="#a5a49e", linewidth=0.9, label="Media (incluye ruidos momentáneos)")
    ax.plot(f[m], db(mediana[m]), color=TINTA, linewidth=1.1, label="Mediana (ruido constante)")
    ultimo = 0.0
    for frec, _ in lista:
        y = db(mediana[np.argmin(np.abs(f - frec))])
        ax.plot(frec, y, "v", color="#e34948", markersize=6, markeredgecolor="white")
        if frec > ultimo * 1.12:  # no encima textos de picos muy cercanos (el resto sale en la consola)
            ax.annotate(f"{frec:.0f}", (frec, y), xytext=(0, 7), textcoords="offset points", ha="center",
                        fontsize=8, color=TINTA2)
            ultimo = frec
    ax.legend(loc="upper right", fontsize=8, frameon=False, labelcolor=TINTA2)


def graficar_diferencia(ax, difs):
    ejes(ax, "(voz + ruido) − ruido [dB]")
    ax.axhline(3, color=TINTA2, linewidth=1, linestyle=(0, (2, 2)))
    ax.text(21, 3.6, "3 dB: voz y ruido iguales", fontsize=8, color=TINTA2)
    ax.axvline(8000, color=TINTA2, linewidth=0.8)
    ax.text(8200, 0.98, "se pierde a 16 kHz", fontsize=8, color=TINTA2, va="top",
            transform=ax.get_xaxis_transform())
    for e, d in difs.items():
        ax.plot(TERCIOS, d, TRAZO[e], color=COLOR[e], linewidth=2, label=e)
        i = int(np.argmax(d))
        ax.annotate(e, (TERCIOS[i], d[i]), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9,
                    color=TINTA, bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8})
    ax.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=TINTA2)


# ----------------------------------------------------------------- en vivo
class EnVivo:
    """Entrada continua sin guardar nada: el callback solo encola los bloques y la ventana los procesa."""

    def __init__(self, entrada):
        import pyaudio
        self.desborde, self.continuar = pyaudio.paInputOverflow, pyaudio.paContinue
        self.canales, self.canal = entrada["canales"], entrada["canal"]
        self.cola, self.sec, self.esperado = deque(maxlen=int(10 * pf.FS / SALTO)), 0, 0
        self.pa = pyaudio.PyAudio()
        try:
            self.stream = self.pa.open(format=pyaudio.paInt24, channels=self.canales, rate=pf.FS, input=True,
                                       input_device_index=entrada["dispositivo"], frames_per_buffer=SALTO,
                                       stream_callback=self._recibir)
        except OSError as e:
            self.pa.terminate()
            sys.exit(f"No se pudo abrir la entrada: {e}")

    def _recibir(self, datos, _n, _info, estado):
        self.cola.append((self.sec, datos, bool(estado & self.desborde)))
        self.sec += 1
        return None, self.continuar

    def leer(self):
        """[(muestras entre -1 y 1, hubo_corte)] de los bloques nuevos. Hay corte si el sistema perdió audio o si la
        cola se llenó (p. ej. al arrastrar la ventana): la señal no es continua y no se debe transformar junta."""
        bloques = []
        while self.cola:
            sec, datos, desborde = self.cola.popleft()
            x = pf.a_int32(datos, self.canales)[:, self.canal - 1] / 2 ** 31
            bloques.append((x, desborde or sec != self.esperado))
            self.esperado = sec + 1
        return bloques

    def detener(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()


class Analizador:
    """Tramas de Hann con traslape sobre un flujo continuo; guarda las de los últimos HISTORIAL segundos."""

    def __init__(self, fs):
        self.fs, self.f = fs, np.fft.rfftfreq(NVIVO, 1 / fs)
        self.ventana = np.hanning(NVIVO + 1)[:-1]
        self.escala = 2 / (fs * (self.ventana ** 2).sum())
        self.pendiente = np.zeros(0)
        self.memoria = np.zeros((int(HISTORIAL * fs / SALTO), len(self.f)), dtype=np.float32)
        self.n = 0                      # tramas calculadas en total
        self.picos = deque(maxlen=max(1, int(fs / SALTO)))

    def agregar(self, x, corte):
        """Suma un bloque y devuelve las tramas nuevas (n, frecuencias), en potencia por Hz."""
        self.pendiente = x if corte else np.concatenate([self.pendiente, x])
        self.picos.append(np.abs(x).max() if len(x) else 0.0)
        nuevas = []
        while len(self.pendiente) >= NVIVO:
            y = self.pendiente[:NVIVO]
            nuevas.append(np.abs(np.fft.rfft((y - y.mean()) * self.ventana)) ** 2 * self.escala)
            self.pendiente = self.pendiente[SALTO:]
        for s in nuevas:
            self.memoria[self.n % len(self.memoria)] = s
            self.n += 1
        return np.array(nuevas)

    def actual(self):
        k = min(self.n, max(1, int(PROMEDIO_VIVO * self.fs / SALTO)))
        return self.memoria[(np.arange(self.n - k, self.n)) % len(self.memoria)].mean(axis=0)

    def mediana(self):
        # 1 de cada 4 tramas basta, porque se traslapan 87 %. / ln 2: la mediana de una potencia con distribución
        # exponencial, llevada a su media (como en Welch)
        return np.median(self.memoria[:min(self.n, len(self.memoria)):4], axis=0) / np.log(2)

    def recientes(self):
        """Todas las tramas guardadas, de la más reciente a la más antigua."""
        k = min(self.n, len(self.memoria))
        return self.memoria[(self.n - 1 - np.arange(k)) % len(self.memoria)]


class Columnas:
    """Reparte las frecuencias de una vista en COLUMNAS. Donde caben varias por columna toma el máximo, para que un
    tono no se diluya; donde no, interpola. Trabaja en dB."""

    def __init__(self, f, f1, f2, logaritmica):
        bordes = np.geomspace(f1, f2, COLUMNAS + 1) if logaritmica else np.linspace(f1, f2, COLUMNAS + 1)
        self.centros = np.sqrt(bordes[:-1] * bordes[1:]) if logaritmica else (bordes[:-1] + bordes[1:]) / 2
        ini, fin = np.searchsorted(f, bordes[:-1]), np.searchsorted(f, bordes[1:])
        escasas = np.flatnonzero(fin - ini < 2)
        self.k = escasas[-1] + 1 if len(escasas) else 0   # desde aquí, todas tienen al menos 2 frecuencias
        self.ini, self.tope = ini[self.k:], fin[-1]
        pos = self.centros[:self.k] / (f[1] - f[0])
        self.j = np.minimum(pos.astype(int), len(f) - 2)
        self.w = pos - self.j

    def _reducir(self, d, funcion):
        r = np.empty(d.shape[:-1] + (COLUMNAS,), dtype=np.float32)
        r[..., :self.k] = d[..., self.j] * (1 - self.w) + d[..., self.j + 1] * self.w
        if self.k < COLUMNAS:
            r[..., self.k:] = funcion.reduceat(d[..., :self.tope], self.ini, axis=-1)
        return r

    def maximo(self, d):
        return self._reducir(d, np.maximum)

    def envolvente(self, d):
        """Mínimo y máximo de cada columna, alternados: se ve igual que la curva completa con muchos menos puntos."""
        return np.stack([self._reducir(d, np.minimum), self._reducir(d, np.maximum)], axis=-1).ravel()


class Monitor:
    def __init__(self, fuente, titulo, fs=pf.FS):
        self.fuente, self.an, self.titulo = fuente, Analizador(fs), titulo
        self.filas = len(self.an.memoria)
        self.pausado, self.escalado, self.cortes = False, False, 0
        self.t_audio, self.t_mediana, self.med = time.monotonic(), 0.0, None
        self.norma = Normalize(-150, -60)
        self.paleta = plt.get_cmap(CALOR)(np.arange(256), bytes=True)
        self.mapa = np.full((self.filas, COLUMNAS), -300, dtype=np.float32)   # dB; -300 = todavía sin datos

        self.fig = plt.figure(figsize=(12, 8.5), layout="constrained")
        g = self.fig.add_gridspec(2, 2, width_ratios=(60, 1), height_ratios=(1, 1.3))
        a1 = self.a1 = self.fig.add_subplot(g[0, 0])
        a2 = self.a2 = self.fig.add_subplot(g[1, 0], sharex=a1)
        a1.set_ylabel("dBFS / Hz", color=TINTA2)
        a1.set_ylim(-150, -60)
        a1.grid(True, color=TENUE, linewidth=0.6)
        a1.set_axisbelow(True)
        self.red = [a1.axvline(0, color="#e34948", linewidth=0.8, alpha=0.3,
                               label="60 Hz y armónicos" if k == 1 else None) for k in range(1, 17)]
        self.graves = a1.axvspan(0, 1, color=TENUE, alpha=0.45, linewidth=0, label="Debajo de 80 Hz")
        self.l_med, = a1.plot([], [], color=TINTA, linewidth=1.2, label="Mediana de 30 s (ruido constante)")
        self.l_act, = a1.plot([], [], color="#2a78d6", linewidth=1.0, label="Último segundo")
        a1.legend(loc="upper right", fontsize=8, frameon=False, labelcolor=TINTA2)
        self.lectura = a1.text(0.012, 0.965, "Esperando audio…", transform=a1.transAxes, va="top", fontsize=10,
                               color=TINTA, linespacing=1.5,
                               bbox={"facecolor": "white", "edgecolor": TENUE, "alpha": 0.9, "pad": 4})

        # La imagen se entrega ya coloreada y solo se colorean las filas nuevas: es lo que más tiempo tomaba
        self.im = a2.imshow(self.colorear(self.mapa), aspect="auto", interpolation="nearest",
                            extent=(0, 1, HISTORIAL, 0))
        a2.set_ylabel("Hace [s]", color=TINTA2)
        a2.set_xlabel("Frecuencia [Hz]", color=TINTA2)
        a1.tick_params(colors=TINTA2, labelbottom=False)
        a2.tick_params(colors=TINTA2)
        self.guias = [a2.axvline(0, color="white", linewidth=0.8, alpha=0.6, linestyle=(0, (3, 3))) for _ in (80, 8000)]
        self.escala = ScalarMappable(self.norma, CALOR)
        barra = self.fig.colorbar(self.escala, cax=self.fig.add_subplot(g[1, 1]))
        barra.set_label("dBFS / Hz (máximo por columna)", color=TINTA2, fontsize=8)
        barra.ax.tick_params(colors=TINTA2, labelsize=8)
        for ax in (a1, a2):
            for lado in ("top", "right"):
                ax.spines[lado].set_visible(False)
        self.poner_vista("1", dibujar=False)
        self.fig.canvas.mpl_connect("key_press_event", self.tecla)
        self.animacion = FuncAnimation(self.fig, self.cuadro, interval=REFRESCO_MS, blit=True, cache_frame_data=False)

    # La animación solo redibuja estos (blit): el dibujo completo le quita tiempo al hilo que recibe el audio
    def artistas(self):
        return [self.im, *self.guias, self.l_med, self.l_act, self.lectura]

    def colorear(self, d):
        x = (d - self.norma.vmin) / (self.norma.vmax - self.norma.vmin)
        return self.paleta[(np.clip(x, 0, 1) * 255).astype(np.uint8)]

    def tecla(self, evento):
        if evento.key == " ":
            self.pausado = not self.pausado
        elif evento.key in ("a", "A"):
            self.ajustar_escala()
        elif evento.key in VISTAS:
            self.poner_vista(evento.key)

    def poner_vista(self, clave, dibujar=True):
        """Cambia el rango y la escala de frecuencia; el mapa se rehace con las tramas guardadas, también en pausa."""
        nombre, f1, f2, logaritmica, marcas = VISTAS[clave]
        # en la vista logarítmica los ejes van en log10(f), para compartir el eje con la imagen
        pos = (lambda v: np.log10(np.maximum(v, 1e-3))) if logaritmica else (lambda v: np.asarray(v, dtype=float))
        self.col = Columnas(self.an.f, f1, f2, logaritmica)
        self.x = np.repeat(pos(self.col.centros), 2)
        x1, x2 = float(pos(f1)), float(pos(f2))
        margen = 0.004 * (x2 - x1)      # en el borde exacto, el blit deja residuos
        self.im.set_extent((x1, x2, HISTORIAL, 0))
        self.a2.set_xlim(x1 - margen, x2 + margen)
        self.a2.set_ylim(HISTORIAL, 0)
        self.a2.set_xticks(pos(marcas), [etiqueta_hz(m) for m in marcas])
        for k, linea in enumerate(self.red, start=1):
            linea.set_xdata([pos(60 * k)] * 2)
        izq = float(pos(f1)) - margen
        self.graves.set_x(izq)
        self.graves.set_width(float(pos(80)) - izq)
        for guia, v in zip(self.guias, (80, 8000)):
            guia.set_xdata([pos(v)] * 2)
        # la lectura del cursor en la barra de la ventana, en Hz
        for ax, unidad in ((self.a1, "dBFS/Hz"), (self.a2, "s")):
            ax.format_coord = lambda x, y, u=unidad: f"{10 ** x if logaritmica else x:.1f} Hz, {y:.1f} {u}"
        self.a1.set_title(f"{self.titulo}\nVista {clave}: {nombre}   ·   1 2 3 vista · Espacio pausa · A escala",
                          loc="left", color=TINTA, fontsize=10)
        self.mapa[:] = -300
        if self.an.n:
            r = self.col.maximo(db(self.an.recientes()))
            self.mapa[:len(r)] = r
        self.recolorear()
        if dibujar:
            self.curvas()
            self.fig.canvas.draw()

    def recolorear(self):
        self.rgba = self.colorear(self.mapa)
        self.im.set_data(self.rgba)

    def ajustar_escala(self):
        """Escala fija según el ruido constante de este momento, para que los cambios se vean contra él."""
        if self.med is None:
            return
        d = db(self.med[(self.an.f >= 20) & (self.an.f <= 20000)])
        bajo, alto = 5 * np.floor(np.percentile(d, 2) / 5) - 5, 5 * np.ceil(d.max() / 5) + 20
        self.a1.set_ylim(bajo, alto)
        self.norma.vmin, self.norma.vmax = bajo + 5, alto - 5
        self.recolorear()
        self.fig.canvas.draw()   # números de los ejes y de la barra de color

    def curvas(self):
        if self.med is not None:
            self.l_act.set_data(self.x, self.col.envolvente(db(self.an.actual())))
            self.l_med.set_data(self.x, self.col.envolvente(db(self.med)))

    def cuadro(self, _):
        ahora = time.monotonic()
        bloques = self.fuente.leer()   # en pausa también se leen, para no acumular audio viejo
        if bloques:
            self.t_audio = ahora
        if self.pausado:
            # lo que llega en pausa se descarta: al reanudar se empieza con un bloque limpio
            self.an.pendiente = np.zeros(0)
            self.lectura.set_text("PAUSA · Espacio para continuar")
            return self.artistas()
        nuevas = []
        for x, corte in bloques:
            self.cortes += corte
            nuevas.extend(self.an.agregar(x, corte))
        if nuevas:
            k = min(len(nuevas), self.filas)
            filas = self.col.maximo(db(np.array(nuevas[-k:])))[::-1]
            self.mapa = np.roll(self.mapa, k, axis=0)
            self.rgba = np.roll(self.rgba, k, axis=0)
            self.mapa[:k], self.rgba[:k] = filas, self.colorear(filas)
            self.im.set_data(self.rgba)
        if self.an.n:
            if self.med is None or ahora - self.t_mediana > 1:
                self.med, self.t_mediana = self.an.mediana(), ahora
            act, f = self.an.actual(), self.an.f
            self.curvas()
            if not self.escalado and self.an.n * SALTO / self.an.fs > 3:
                self.escalado = True
                self.ajustar_escala()
            pico = 20 * np.log10(max(max(self.an.picos), 1e-9))
            texto = (f"80–8000 Hz: {nivel(f, act, 80, 8000):6.1f} dBFS   (constante {nivel(f, self.med, 80, 8000):.1f})\n"
                     f"20–80 Hz: {nivel(f, act, 20, 80):6.1f} dBFS   (constante {nivel(f, self.med, 20, 80):.1f})\n"
                     f"Pico: {pico:.1f} dBFS" + ("   SATURA: baja la ganancia" if pico >= SATURA_DBFS else ""))
            if self.cortes:
                texto += f"   ·   Cortes de audio: {self.cortes}"
            self.lectura.set_text(texto)
            self.lectura.set_color("#c22f2e" if pico >= SATURA_DBFS else TINTA)
        if ahora - self.t_audio > 2:
            self.lectura.set_text("SIN AUDIO: revisa la interfaz y el cable")
        return self.artistas()


# ----------------------------------------------------------------- modos
def entrada_de(dispositivo):
    config = None if dispositivo is not None else pf.cargar_config()
    entrada = config[0] if config else pf.elegir_entrada(dispositivo)
    print(f"Entrada: «{entrada['nombre']}» ({entrada.get('api')}), canal {entrada['canal']}")
    pf.avisar_api(entrada)
    return entrada


def en_vivo(dispositivo):
    entrada = entrada_de(dispositivo)
    fuente = EnVivo(entrada)
    try:
        monitor = Monitor(fuente, f"En vivo: {entrada['nombre']} ({entrada.get('api')}), canal {entrada['canal']}")
        plt.show()
    finally:
        fuente.detener()
    return monitor


def medir(segundos, dispositivo):
    entrada = entrada_de(dispositivo)
    input(f"Presiona Enter y guarda silencio {segundos:.0f} s (se descarta {RECORTE:.0f} s en cada extremo)...")
    grab = pf.Grabador(entrada)
    total = segundos + 2 * RECORTE
    limite = time.monotonic() + total + 5
    while grab.tiempo() < total and time.monotonic() < limite:
        print(f"\r  {max(0.0, total - grab.tiempo()):4.0f} s ", end="", flush=True)
        time.sleep(0.2)
    audio = grab.detener()
    print()
    if len(audio) < total * pf.FS * 0.9:
        sys.exit(f"Solo llegaron {len(audio) / pf.FS:.1f} s de audio. Revisa la interfaz.")
    carpeta = pf.CARPETA_SALIDA / f"ruido_{datetime.datetime.now():%Y%m%d_%H%M%S}"
    carpeta.mkdir(parents=True, exist_ok=True)
    soundfile.write(carpeta / "audio.wav", audio, pf.FS, subtype="PCM_24")
    r = int(RECORTE * pf.FS)
    x = audio[r:-r].astype(np.float64) / 2 ** 31
    f, mediana, media = densidad(x, pf.FS)
    lista = informe_ruido(f, mediana, media, pf.FS)
    fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    graficar_ruido(ax, f, mediana, media, lista)
    ax.set_xlabel("Frecuencia [Hz]", color=TINTA2)
    ax.set_title(f"Ruido del lugar, {carpeta.name[6:]}", loc="left", color=TINTA)
    return fig, carpeta


def buscar_sesion(nombre):
    if nombre == "ultima":
        sesiones = [d for d in pf.CARPETA_SALIDA.glob("P*_*") if (d / "audio.wav").exists()]
        if not sesiones:
            sys.exit(f"No hay sesiones en {pf.CARPETA_SALIDA}")
        return max(sesiones, key=lambda d: d.name.split("_", 1)[1])
    carpeta = Path(nombre) if Path(nombre).is_dir() else pf.CARPETA_SALIDA / nombre
    if not (carpeta / "audio.wav").exists():
        sys.exit(f"No existe {carpeta / 'audio.wav'}")
    return carpeta


def comparar(nombre):
    carpeta = buscar_sesion(nombre)
    with open(carpeta / "frases.csv", newline="", encoding="utf-8") as a:
        filas = [(r["tipo"], r["estilo"], float(r["inicio_s"]), float(r["fin_s"])) for r in csv.DictReader(a)
                 if r["fin_s"] and r["interrumpida"] == "0" and r["repetida"] == "0"]
    with soundfile.SoundFile(carpeta / "audio.wav") as wav:
        fs = wav.samplerate

        def leer(t1, t2):
            wav.seek(int(t1 * fs))
            return wav.read(int((t2 - t1) * fs), dtype="float64")

        silencio = [(a + RECORTE, b - RECORTE) for t, _, a, b in filas if t == "silencio_referencia"]
        if not silencio or silencio[-1][1] - silencio[-1][0] < 5:
            sys.exit("La sesión no tiene un silencio de referencia completo.")
        ruido = leer(*silencio[-1])
        f, mediana, media = densidad(ruido, fs)
        print(f"Sesión {carpeta.name}: silencio de {len(ruido) / fs:.0f} s")
        lista = informe_ruido(f, mediana, media, fs)
        # bandas de la comparación: tercios de octava, las de la tabla y 100-8000 Hz para decidir qué trama tiene voz
        raiz6 = 2 ** (1 / 6)
        limites = [(c / raiz6, c * raiz6) for c in TERCIOS] + list(BANDAS) + [(100, 8000)]
        tr = tramas(ruido, fs, limites)
        umbral = np.percentile(tr[:, -1], 95)
        # mediana por banda: los golpes durante el silencio no cuentan como ruido constante
        base, base_media = np.median(tr, axis=0), tr.mean(axis=0)
        n = len(TERCIOS)
        difs, tabla = {}, []
        for e in ESTILOS:
            partes = [tramas(leer(a, b), fs, limites) for t, est, a, b in filas
                      if est == e and t != "silencio_referencia" and b - a >= MIN_FILA]
            if not partes:
                continue
            tv = np.concatenate(partes)
            activa = tv[tv[:, -1] > umbral]
            if len(activa) < 20:
                print(f"  {e}: casi no hay tramas por encima del ruido.")
                continue
            voz = np.median(activa, axis=0)  # la media la dominan unas cuantas ráfagas fuertes
            difs[e] = db(voz[:n]) - db(base[:n])
            tabla.append((e, len(tv) * NTRAMA / 2 / fs, 100 * len(activa) / len(tv),
                          db(voz[n:-1]) - db(base[n:-1]), db(voz[n:-1]) - db(base_media[n:-1])))
    print("\n(voz + ruido) - ruido, en dB. Primero contra la mediana del ruido y, entre paréntesis, contra su media")
    print("  estilo     dur   activo  " + "".join(f"{f'{a}-{b}':>16}" for a, b in BANDAS))
    for e, dur, act, d1, d2 in tabla:
        celdas = "".join(f"{f'{x:.0f} ({y:.0f})':>16}" for x, y in zip(d1, d2))
        print(f"  {e:<8} {dur:5.0f} s {act:5.0f} %  {celdas}")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 9), layout="constrained", sharex=True)
    graficar_ruido(a1, f, mediana, media, lista)
    a1.set_title(f"Ruido del silencio de referencia, {carpeta.name}", loc="left", color=TINTA)
    graficar_diferencia(a2, difs)
    a2.set_title("Voz sobre el ruido constante, por tercio de octava", loc="left", color=TINTA)
    a2.set_xlabel("Frecuencia [Hz]", color=TINTA2)
    return fig, carpeta


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sesion", help="carpeta de una sesión, o «ultima»; sin esta opción ni --vivo, mide ahora")
    p.add_argument("--vivo", action="store_true", help="curva y mapa de calor en tiempo real (no graba)")
    p.add_argument("--segundos", type=float, default=SEGUNDOS, help="duración de la medición")
    p.add_argument("--dispositivo", type=int, default=None, help="índice de la entrada (si no, config_audio.json)")
    p.add_argument("--sin-ventana", action="store_true", help="solo guarda la figura")
    a = p.parse_args()
    if a.vivo:
        if a.sesion or a.sin_ventana:
            p.error("--vivo no se combina con --sesion ni con --sin-ventana")
        en_vivo(a.dispositivo)
        return
    fig, carpeta = comparar(a.sesion) if a.sesion else medir(a.segundos, a.dispositivo)
    fig.savefig(carpeta / "espectro.png", dpi=150)
    print(f"\nFigura guardada en {carpeta / 'espectro.png'}")
    if not a.sin_ventana:
        plt.show()


if __name__ == "__main__":
    main()
