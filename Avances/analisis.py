import os
import numpy as np
import matplotlib.pyplot as plt
import pyaudio # pip install pyaudio

## Parámetros iniciales

SAMPLE_RATE = 16000
SALIDAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SALIDAS")
ARCHIVO     = os.path.join(SALIDAS_DIR, "grabacion_ruido.npy")
CHUNK       = 512
MIC_ACTIVO  = 1 # Numeración natural, no empieza en 0

## Cargar audio

audio = np.load(ARCHIVO)
print(f"Shape: {audio.shape}  |  {len(audio)/SAMPLE_RATE:.2f} s | Micrófono activo: {MIC_ACTIVO}")

# Cada columna es un micrófono independiente
microfonos = {k+1: audio[:, k] for k in range(8)}

## Graficar todos los micrófonos

t = np.linspace(0, len(audio) / SAMPLE_RATE, num=len(audio))

fig, axes = plt.subplots(8, 2, figsize=(14, 20), sharex="col")
fig.suptitle("8 micrófonos — onda y FFT", fontsize=13, fontweight="bold")

for i in range(8):
    sig   = audio[:, i]
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / SAMPLE_RATE)
    mag   = np.abs(np.fft.rfft(sig))

    axes[i, 0].plot(t, sig, linewidth=0.4, color="#2196F3")
    axes[i, 0].set_ylabel(f"Mic{i+1}", fontsize=9)
    axes[i, 0].grid(True, alpha=0.3)

    axes[i, 1].plot(freqs, mag, linewidth=0.4, color="#E91E63")
    axes[i, 1].set_xlim(0, SAMPLE_RATE // 2)
    axes[i, 1].grid(True, alpha=0.3)

axes[0, 0].set_title("Onda")
axes[0, 1].set_title("FFT")
axes[-1, 0].set_xlabel("Tiempo (s)")
axes[-1, 1].set_xlabel("Frecuencia (Hz)")

plt.tight_layout()
plt.show()

## Reproducir

# Señal con la que trabajar
señal = microfonos[MIC_ACTIVO] 

pcm = (señal * 32768).clip(-32768, 32767).astype(np.int16) # 16 bits con signo

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, output=True)
for i in range(0, len(pcm), CHUNK):
    stream.write(pcm[i : i + CHUNK].tobytes())
stream.stop_stream()
stream.close()
p.terminate()

## Zona de pruebas
