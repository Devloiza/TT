"""
das.py — Delay-and-sum (DAS) con retardos fraccionarios, SRP y GCC-PHAT.

Convención de retardos: tau[m] es el tiempo de llegada (relativo, s) del
frente de onda al micrófono m. Para alinear, cada canal se retrasa
max(tau) - tau[m] >= 0 (causal: la salida queda alineada con el último
micrófono en recibir la señal, como tendrá que ser en tiempo real).

Los retardos se aplican en frecuencia (multiplicar por e^{-j2πfd}), así
que no se redondean a muestras enteras: a 16 kHz una muestra son 62.5 µs
(~2.1 cm de recorrido) y los retardos entre micrófonos de un arreglo de
~10 cm son de 0 a ~5 muestras, casi nunca enteros.

Todo vectorizado con NumPy (ver CLAUDE.md: nada de loops de Python por
muestra/canal en lo que vaya a terminar en el pipeline en tiempo real).

Limitación conocida: el retardo por FFT es circular sobre el frame, con
transitorios en los bordes. Para tiempo real hará falta overlap-save entre
frames consecutivos; aquí se evalúa sobre el interior de la señal.
"""

import numpy as np

from campo import C_SONIDO, vector_direccion


# ── Retardos de apuntamiento (steering) ───────────────────────────────────────

def retardos_campo_lejano(posiciones, azimut_deg, elevacion_deg=0.0, c=C_SONIDO):
    """
    Retardos de onda plana. azimut_deg puede ser escalar o arreglo (A,);
    devuelve (M,) o (A, M). Referidos al centroide del arreglo.
    """
    centrada = posiciones - posiciones.mean(axis=0)
    u = vector_direccion(np.asarray(azimut_deg, float), elevacion_deg)   # (..., 3)
    return -(u @ centrada.T) / c


def retardos_campo_cercano(posiciones, punto, c=C_SONIDO):
    """Retardos esféricos hacia uno o varios puntos (3,) o (A, 3); devuelve (M,) o (A, M)."""
    punto = np.asarray(punto, float)
    return np.linalg.norm(punto[..., None, :] - posiciones, axis=-1) / c


# ── Retardo fraccionario y DAS ────────────────────────────────────────────────

def _nfft(n, extra):
    return 1 << int(np.ceil(np.log2(n + extra + 1)))


def alinear(frame, tau, fs):
    """Retrasa cada canal max(tau) - tau[m] segundos. frame (N, M) -> (N, M)."""
    n = frame.shape[0]
    d = tau.max() - tau                                   # (M,) >= 0
    nfft = _nfft(n, int(np.ceil(d.max() * fs)))
    X = np.fft.rfft(frame, nfft, axis=0)                  # (F, M)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    Y = X * np.exp(-2j * np.pi * f[:, None] * d[None, :])
    return np.fft.irfft(Y, nfft, axis=0)[:n]


def das(frame, tau, fs, pesos=None):
    """
    Delay-and-sum: alinea con `tau` y suma ponderada. frame (N, M) -> (N,).
    pesos=None => uniformes 1/M (DAS convencional). Pesos arbitrarios
    permiten probar los "pesos diferenciados" del protocolo (D2); se
    normalizan a suma 1 para que la ganancia en la dirección de mirada sea 1.
    """
    m = frame.shape[1]
    w = np.full(m, 1 / m) if pesos is None else np.asarray(pesos, float) / np.sum(pesos)
    return alinear(frame, tau, fs) @ w


# ── Localización ──────────────────────────────────────────────────────────────

def srp(frame, posiciones, azimuts_deg, fs, c=C_SONIDO, pesos=None, phat=False,
        fmin=100.0, fmax=None, bloque=32):
    """
    Steered Response Power: energía de la salida DAS apuntada a cada azimut
    (campo lejano). Devuelve P (A,) — el máximo es la DOA estimada.
    phat=True blanquea el espectro (SRP-PHAT); no usar con un tono puro, porque
    amplificaría bins sin señal.
    """
    n, m = frame.shape
    w = np.full(m, 1 / m) if pesos is None else np.asarray(pesos, float) / np.sum(pesos)
    X = np.fft.rfft(frame, axis=0)
    f = np.fft.rfftfreq(n, 1 / fs)
    banda = (f >= fmin) & (f <= (fmax or fs / 2))
    X, f = X[banda], f[banda]
    if phat:
        X = X / (np.abs(X) + 1e-12)
    Xw = X * w                                            # (F, M)

    azimuts_deg = np.asarray(azimuts_deg, float)
    P = np.empty(len(azimuts_deg))
    for i in range(0, len(azimuts_deg), bloque):          # bloques de ángulos para acotar memoria
        tau = retardos_campo_lejano(posiciones, azimuts_deg[i:i + bloque], c=c)    # (A, M)
        steer = np.exp(2j * np.pi * f[None, :, None] * tau[:, None, :])           # (A, F, M)
        P[i:i + bloque] = np.sum(np.abs(np.einsum("afm,fm->af", steer, Xw)) ** 2, axis=1)
    return P


def gcc_phat(x, ref, fs, max_tau=None, interp=16):
    """
    Retardo (s) de x respecto a ref por GCC-PHAT, con resolución 1/interp
    muestras. Positivo = x llega después que ref. Ambiguo para un tono puro.
    """
    n = len(x) + len(ref)
    G = np.fft.rfft(x, n) * np.conj(np.fft.rfft(ref, n))
    cc = np.fft.irfft(G / (np.abs(G) + 1e-12), n * interp)
    max_shift = n * interp // 2
    if max_tau is not None:
        max_shift = min(int(np.ceil(interp * fs * max_tau)), max_shift)
    cc = np.concatenate([cc[-max_shift:], cc[:max_shift + 1]])
    return (np.argmax(np.abs(cc)) - max_shift) / (interp * fs)
