import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf

SAMPLE_RATE = 44100

## MÁSCARAS

def pasa_bajos(freqs, corte_hz):
    return (freqs < corte_hz).astype(float)

def pasa_altos(freqs, corte_hz):
    return (freqs > corte_hz).astype(float)

def pasa_banda(freqs, f_min, f_max):
    return ((freqs >= f_min) & (freqs <= f_max)).astype(float)

def notch(freqs, f_centro, ancho_hz=50):
    mascara = np.ones(len(freqs), dtype=float)
    mascara[(freqs >= f_centro - ancho_hz / 2) & (freqs <= f_centro + ancho_hz / 2)] = 0.0
    return mascara

## APLICAR FILTRO

def aplicar_filtro(audio_np: np.ndarray, mascara: np.ndarray) -> np.ndarray:
    """FFT → multiplicar por máscara → IFFT. Devuelve int16."""
    audio_f  = audio_np.astype(np.float32) / 32768.0
    espectro = np.fft.rfft(audio_f)
    filtrado = np.fft.irfft(espectro * mascara, n=len(audio_f))
    return (filtrado * 32768.0).clip(-32768, 32767).astype(np.int16)

## GRAFICAR COMPARACIÓN DE FILTROS

def graficar_filtros(audio_np: np.ndarray, resultados: dict, sample_rate=SAMPLE_RATE):
    """
    resultados = {"nombre": audio_int16, ...}
    Muestra forma de onda y espectro para cada variante.
    """
    n_filtros = len(resultados)
    fig, axes = plt.subplots(2, n_filtros, figsize=(5 * n_filtros, 7))
    fig.suptitle("Filtrado con Fourier", fontsize=13, fontweight="bold")

    audio_f = audio_np.astype(np.float32) / 32768.0
    tiempo  = np.linspace(0, len(audio_f) / sample_rate, num=len(audio_f))
    freqs_orig = np.fft.rfftfreq(len(audio_f), d=1.0 / sample_rate)

    colores = ["#2196F3", "#4CAF50", "#FF5722", "#9C27B0", "#FF9800"]

    for col, (nombre, señal) in enumerate(resultados.items()):
        señal_f = señal.astype(np.float32) / 32768.0
        color   = colores[col % len(colores)]
        t_var   = np.linspace(0, len(señal_f) / sample_rate, num=len(señal_f))

        ax = axes[0, col]
        ax.plot(t_var, señal_f, color=color, linewidth=0.4)
        ax.set_title(nombre, fontsize=9, fontweight="bold")
        ax.set_ylim(-1.1, 1.1)
        ax.set_xlabel("Tiempo (s)")
        ax.set_ylabel("Amplitud" if col == 0 else "")
        ax.grid(True, alpha=0.3)

        ax = axes[1, col]
        mag = np.abs(np.fft.rfft(señal_f))
        freqs_v = np.fft.rfftfreq(len(señal_f), d=1.0 / sample_rate)
        ax.fill_between(freqs_v, mag, color=color, alpha=0.6, linewidth=0)
        ax.set_xlim(0, sample_rate // 2)
        ax.set_xlabel("Frecuencia (Hz)")
        ax.set_ylabel("|FFT|" if col == 0 else "")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("filtros_fourier.png", dpi=150, bbox_inches="tight")
    print("Gráfica guardada en: filtros_fourier.png")
    plt.show()

## GUARDAR VARIANTES FILTRADAS

def guardar_filtros(resultados: dict, sample_rate=SAMPLE_RATE):
    for nombre, señal in resultados.items():
        archivo = f"{nombre.replace(' ', '_')}.wav"
        sf.write(archivo, señal, sample_rate, subtype="PCM_16")
        print(f"Guardado: {archivo}")