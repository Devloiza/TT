"""
stage1b_record_plot.py — Etapa 1b: graba audio real de 1 mic y lo verifica.

Uso:
    python stage1b_record_plot.py COM8 [segundos]

Verifica la tasa de bytes (misma señal de integridad de la Etapa 1a) y
grafica la forma de onda + espectro para confirmar visualmente que el
micrófono está capturando señal real (no silencio ni ruido plano).
"""

import sys
import time
import serial
import numpy as np
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("Uso: python stage1b_record_plot.py <PUERTO> [segundos]")
    sys.exit(1)

puerto = sys.argv[1]
dur    = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
BAUD   = 3000000
RATE   = 16000

ser = serial.Serial(puerto, BAUD, timeout=1)
print(f"Grabando {dur:.1f}s desde {puerto} @ {BAUD} baud...")

buf = bytearray()
t_start = time.time()
while time.time() - t_start < dur:
    dato = ser.read(4096)
    if dato:
        buf += dato
ser.close()

n_bytes = len(buf)
rate = n_bytes / dur
print(f"\nBytes recibidos : {n_bytes}  (~{rate:.0f} B/s, esperado ~32000 B/s)")

audio = np.frombuffer(bytes(buf[: (n_bytes // 2) * 2]), dtype="<i2").astype(np.float32) / 32768.0
print(f"Muestras        : {len(audio)}  (~{len(audio)/RATE:.2f} s de audio)")
print(f"RMS             : {np.sqrt(np.mean(audio**2)):.4f}")
print(f"Pico            : {np.max(np.abs(audio)):.4f}")

if np.max(np.abs(audio)) < 0.001:
    print("AVISO: la señal es casi plana — revisa conexión del micrófono.")

t = np.arange(len(audio)) / RATE
freqs = np.fft.rfftfreq(len(audio), d=1.0 / RATE)
mag = np.abs(np.fft.rfft(audio))

fig, axes = plt.subplots(2, 1, figsize=(10, 6))
axes[0].plot(t, audio, linewidth=0.5)
axes[0].set_title("Onda — Mic 1 (Stage 1b)")
axes[0].set_xlabel("Tiempo (s)")
axes[0].grid(True, alpha=0.3)

axes[1].plot(freqs, mag, linewidth=0.5, color="#E91E63")
axes[1].set_xlim(0, RATE // 2)
axes[1].set_title("FFT")
axes[1].set_xlabel("Frecuencia (Hz)")
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
