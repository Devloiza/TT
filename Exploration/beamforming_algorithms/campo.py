"""
campo.py — Simulación del campo acústico ideal (sin reverberación ni ruido ambiental).

Las señales de prueba se definen como funciones CONTINUAS de t, así que la
señal de cada micrófono se evalúa analíticamente en s(t - tau_i): los
retardos fraccionarios son exactos, sin redondeo a muestras enteras. Esto
es lo que permite usar la simulación como verdad de referencia para el DAS.

La salida tiene el mismo formato que produce hilo_sincronizador en
monitor_8LR.py: (N, 8) float32 en [-1, 1].
"""

import numpy as np
from scipy.signal import chirp as _chirp, gausspulse

C_SONIDO = 343.0
FS = 16000


# ── Señales de prueba (callables de t en segundos) ────────────────────────────

def seno(f=1000.0, amplitud=0.5):
    s = lambda t: amplitud * np.sin(2 * np.pi * f * t)
    s.nombre = f"seno {f:g} Hz"
    s.banda_ancha = False
    return s


def chirp(f0=200.0, f1=7000.0, duracion=0.5, amplitud=0.5):
    s = lambda t: amplitud * _chirp(np.mod(t, duracion), f0=f0, t1=duracion, f1=f1)
    s.nombre = f"chirp {f0:g}-{f1:g} Hz"
    s.banda_ancha = True
    return s


def multitono(fmin=200.0, fmax=7000.0, n_tonos=40, rms=0.15, semilla=0):
    """Suma de tonos con frecuencias y fases aleatorias: banda ancha y aún analítica."""
    rng = np.random.default_rng(semilla)
    f = rng.uniform(fmin, fmax, n_tonos)
    fase = rng.uniform(0, 2 * np.pi, n_tonos)
    a = rms * np.sqrt(2 / n_tonos)

    def s(t):
        t = np.asarray(t)
        return a * np.sin(2 * np.pi * f * t[..., None] + fase).sum(axis=-1)

    s.nombre = f"multitono {n_tonos}x {fmin:g}-{fmax:g} Hz"
    s.banda_ancha = True
    return s


def pulso(fc=2000.0, bw=0.8, t0=0.05, amplitud=0.8):
    s = lambda t: amplitud * gausspulse(t - t0, fc=fc, bw=bw)
    s.nombre = f"pulso gaussiano fc={fc:g} Hz"
    s.banda_ancha = True
    return s


SENALES = {"seno": seno, "chirp": chirp, "multitono": multitono, "pulso": pulso}


# ── Geometría fuente-arreglo ──────────────────────────────────────────────────

def vector_direccion(azimut_deg, elevacion_deg=0.0):
    """Vector unitario hacia la fuente. Azimut desde +x, antihorario."""
    az, el = np.deg2rad(azimut_deg), np.deg2rad(elevacion_deg)
    return np.stack([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el),
                     np.sin(el) * np.ones_like(az)], axis=-1)


def fuente_polar(centro, distancia, azimut_deg, altura=0.0):
    """Posición 3D de una fuente a `distancia` (en el plano XY) y `azimut_deg` del centro."""
    return np.asarray(centro, float) + np.array([
        distancia * np.cos(np.deg2rad(azimut_deg)),
        distancia * np.sin(np.deg2rad(azimut_deg)),
        altura])


# ── Simulación ────────────────────────────────────────────────────────────────

def simular(posiciones, fuente, senal, fs=FS, duracion=0.5, c=C_SONIDO,
            modelo="esferico", atenuacion=True):
    """
    Señales en los M micrófonos para una fuente puntual.

    modelo="esferico": propagación real desde el punto `fuente` (campo cercano
        exacto), con atenuación 1/r normalizada a 1 en el centroide si
        atenuacion=True.
    modelo="plano": onda plana que llega desde la dirección de `fuente` vista
        desde el centroide (campo lejano ideal), sin atenuación. Útil para
        verificar el DAS de campo lejano sin error de modelo.

    Devuelve (x, info): x (N, M) float32; info con t, tau (s), ganancias.
    """
    posiciones = np.asarray(posiciones, float)
    fuente = np.asarray(fuente, float)
    centro = posiciones.mean(axis=0)
    r_centro = np.linalg.norm(fuente - centro)

    if modelo == "esferico":
        r = np.linalg.norm(fuente - posiciones, axis=1)
        tau = r / c
        ganancias = r_centro / r if atenuacion else np.ones(len(r))
    elif modelo == "plano":
        u = (fuente - centro) / r_centro
        tau = (r_centro - (posiciones - centro) @ u) / c
        ganancias = np.ones(len(posiciones))
    else:
        raise ValueError(f"modelo desconocido: {modelo!r}")

    t = np.arange(int(round(duracion * fs))) / fs
    x = ganancias * senal(t[:, None] - tau[None, :])
    return x.astype(np.float32), {"t": t, "tau": tau, "ganancias": ganancias}


def ruido_sensor(n, m, snr_db, potencia_senal, semilla=1):
    """Ruido blanco independiente por micrófono (ruido propio del sensor, no ambiental)."""
    rng = np.random.default_rng(semilla)
    sigma = np.sqrt(potencia_senal / 10 ** (snr_db / 10))
    return (sigma * rng.standard_normal((n, m))).astype(np.float32)
